"""Domain tools for the PM Notification Gatekeeper Agent — CF direct-OData mode.

Replaces MCP/Agent Gateway tool invocations with direct OData calls via the
S/4HANA client when running on Cloud Foundry (VCAP_SERVICES present).

Tool names match the Agent Gateway MCP tool names exactly so the LLM behaves
identically on CF and Joule.

OData services covered:
  API_MAINTNOTIFICATION      — maintenance notifications, items, causes, activities
  API_EQUIPMENT              — equipment master data
  API_FUNCTIONALLOCATION     — functional location master data
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from s4hana_client import Client as S4Client

logger = logging.getLogger(__name__)

NOTIF_ROOT = "/sap/opu/odata/sap/API_MAINTNOTIFICATION"
EQUIP_ROOT = "/sap/opu/odata/sap/API_EQUIPMENT"
FLOC_ROOT  = "/sap/opu/odata/sap/API_FUNCTIONALLOCATION"

MAX_PAGE_SIZE = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _odata_params(
    filter: str | None = None,
    select: str | None = None,
    orderby: str | None = None,
    top: int | None = None,
    skip: int | None = None,
    expand: str | None = None,
    inlinecount: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"$format": "json"}
    if filter:
        params["$filter"] = filter
    if select:
        params["$select"] = select
    if orderby:
        params["$orderby"] = orderby
    params["$top"] = min(top, MAX_PAGE_SIZE) if top is not None else MAX_PAGE_SIZE
    if skip is not None:
        params["$skip"] = skip
    if expand:
        params["$expand"] = expand
    if inlinecount:
        params["$inlinecount"] = inlinecount
    return params


def _rj(result: Any) -> str:
    if isinstance(result, dict) and result.get("error"):
        return json.dumps({
            "error": result.get("message", "Unknown error"),
            "status_code": result.get("status_code"),
        })
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Shared input models
# ---------------------------------------------------------------------------

class ODataListInput(BaseModel):
    filter: Optional[str] = Field(default=None, description="OData $filter expression")
    select: Optional[str] = Field(default=None, description="OData $select expression")
    orderby: Optional[str] = Field(default=None, description="OData $orderby expression")
    top: Optional[int] = Field(default=None, description="Maximum number of results (capped at 100)")
    skip: Optional[int] = Field(default=None, description="Number of results to skip for paging")
    expand: Optional[str] = Field(default=None, description="OData $expand expression")
    inlinecount: Optional[str] = Field(default=None, description="OData $inlinecount (allpages or none)")


class ODataGetInput(BaseModel):
    select: Optional[str] = Field(default=None, description="OData $select expression")
    expand: Optional[str] = Field(default=None, description="OData $expand expression")


# ---------------------------------------------------------------------------
# MaintenanceNotification
# ---------------------------------------------------------------------------

class GetNotifInput(ODataGetInput):
    MaintenanceNotification: str = Field(description="Maintenance Notification number")


class ListNotifByNavInput(BaseModel):
    MaintenanceNotification: str = Field(description="Maintenance Notification number")
    filter: Optional[str] = Field(default=None, description="OData $filter expression")
    select: Optional[str] = Field(default=None, description="OData $select expression")
    orderby: Optional[str] = Field(default=None, description="OData $orderby expression")
    top: Optional[int] = Field(default=None, description="Maximum number of results")
    skip: Optional[int] = Field(default=None, description="Number of results to skip")
    expand: Optional[str] = Field(default=None, description="OData $expand expression")
    inlinecount: Optional[str] = Field(default=None, description="OData $inlinecount")


# ---------------------------------------------------------------------------
# MaintenanceNotificationItem
# ---------------------------------------------------------------------------

class GetNotifItemInput(ODataGetInput):
    MaintenanceNotification: str = Field(description="Maintenance Notification number")
    MaintenanceNotificationItem: str = Field(description="Notification item number")


# ---------------------------------------------------------------------------
# MaintNotificationEffectCode
# ---------------------------------------------------------------------------

class GetEffectCodeInput(ODataGetInput):
    MaintNotifEffectCode: str = Field(description="Effect code key")


# ---------------------------------------------------------------------------
# MaintenanceNotificationPartner
# ---------------------------------------------------------------------------

class GetNotifPartnerInput(ODataGetInput):
    MaintenanceNotification: str = Field(description="Maintenance Notification number")
    MaintenanceNotificationPartner: str = Field(description="Partner counter")
    PartnerFunction: str = Field(description="Partner function code")


# ---------------------------------------------------------------------------
# MaintNotificationItemActivity
# ---------------------------------------------------------------------------

class GetNotifItemActivityInput(ODataGetInput):
    MaintenanceNotification: str = Field(description="Maintenance Notification number")
    MaintenanceNotificationItem: str = Field(description="Notification item number")
    MaintNotifItemActivity: str = Field(description="Activity counter")


# ---------------------------------------------------------------------------
# MaintNotificationItemCause
# ---------------------------------------------------------------------------

class GetNotifItemCauseInput(ODataGetInput):
    MaintenanceNotification: str = Field(description="Maintenance Notification number")
    MaintenanceNotificationItem: str = Field(description="Notification item number")
    MaintNotifItemCause: str = Field(description="Cause counter")


# ---------------------------------------------------------------------------
# OData function imports
# ---------------------------------------------------------------------------

class ApproveMaintWorkRequestInput(BaseModel):
    MaintenanceNotification: str = Field(description="Maintenance Notification number to approve")


class CompleteMaintNotificationInput(BaseModel):
    MaintenanceNotification: str = Field(description="Maintenance Notification number to complete")


class RejectMaintWorkRequestInput(BaseModel):
    MaintenanceNotification: str = Field(description="Maintenance Notification number to reject")
    MaintNotifLongTextForRejection: Optional[str] = Field(default=None, description="Rejection reason text")


class SetMaintNotifToInfoRequiredInput(BaseModel):
    MaintenanceNotification: str = Field(description="Maintenance Notification number")


class SetMaintNotifToInProcessInput(BaseModel):
    MaintenanceNotification: str = Field(description="Maintenance Notification number to set in-process")


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------

class GetEquipmentInput(ODataGetInput):
    Equipment: str = Field(description="Equipment number")


# ---------------------------------------------------------------------------
# FunctionalLocation
# ---------------------------------------------------------------------------

class GetFlocInput(ODataGetInput):
    FunctionalLocation: str = Field(description="Functional Location identifier")


class GetFlocLongtextInput(ODataGetInput):
    FunctionalLocation: str = Field(description="Functional Location identifier")
    Language: str = Field(description="Language key (e.g. EN)")


# ---------------------------------------------------------------------------
# Tool builder
# ---------------------------------------------------------------------------

def build_domain_tools(s4: S4Client | None = None) -> list[BaseTool]:
    """Build all PM domain tools wired to the given S4Client."""
    client = s4 or S4Client()

    # ---- MaintenanceNotification ----

    async def list_maintenancenotification(
        filter: str | None = None, select: str | None = None,
        orderby: str | None = None, top: int | None = None,
        skip: int | None = None, expand: str | None = None,
        inlinecount: str | None = None,
    ) -> str:
        params = _odata_params(filter, select, orderby, top, skip, expand, inlinecount)
        return _rj(await client.get(f"{NOTIF_ROOT}/MaintenanceNotification", params=params))

    async def get_maintenancenotification(
        MaintenanceNotification: str,
        select: str | None = None, expand: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"$format": "json"}
        if select: params["$select"] = select
        if expand: params["$expand"] = expand
        return _rj(await client.get(
            f"{NOTIF_ROOT}/MaintenanceNotification('{MaintenanceNotification}')",
            params=params,
        ))

    async def count_maintenancenotification(filter: str | None = None) -> str:
        params: dict[str, Any] = {}
        if filter: params["$filter"] = filter
        result = await client.get(f"{NOTIF_ROOT}/MaintenanceNotification/$count", params=params)
        return _rj(result)

    # ---- MaintNotificationEffectCode ----

    async def list_maintnotificationeffectcode(
        filter: str | None = None, select: str | None = None,
        orderby: str | None = None, top: int | None = None,
        skip: int | None = None, expand: str | None = None,
        inlinecount: str | None = None,
    ) -> str:
        params = _odata_params(filter, select, orderby, top, skip, expand, inlinecount)
        return _rj(await client.get(f"{NOTIF_ROOT}/MaintNotificationEffectCode", params=params))

    async def get_maintnotificationeffectcode(
        MaintNotifEffectCode: str,
        select: str | None = None, expand: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"$format": "json"}
        if select: params["$select"] = select
        if expand: params["$expand"] = expand
        return _rj(await client.get(
            f"{NOTIF_ROOT}/MaintNotificationEffectCode('{MaintNotifEffectCode}')",
            params=params,
        ))

    # ---- MaintenanceNotificationItem ----

    async def list_maintenancenotificationitem(
        filter: str | None = None, select: str | None = None,
        orderby: str | None = None, top: int | None = None,
        skip: int | None = None, expand: str | None = None,
        inlinecount: str | None = None,
    ) -> str:
        params = _odata_params(filter, select, orderby, top, skip, expand, inlinecount)
        return _rj(await client.get(f"{NOTIF_ROOT}/MaintenanceNotificationItem", params=params))

    async def get_maintenancenotificationitem(
        MaintenanceNotification: str, MaintenanceNotificationItem: str,
        select: str | None = None, expand: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"$format": "json"}
        if select: params["$select"] = select
        if expand: params["$expand"] = expand
        key = f"MaintenanceNotificationItem(MaintenanceNotification='{MaintenanceNotification}',MaintenanceNotificationItem='{MaintenanceNotificationItem}')"
        return _rj(await client.get(f"{NOTIF_ROOT}/{key}", params=params))

    async def count_maintenancenotificationitem(filter: str | None = None) -> str:
        params: dict[str, Any] = {}
        if filter: params["$filter"] = filter
        return _rj(await client.get(f"{NOTIF_ROOT}/MaintenanceNotificationItem/$count", params=params))

    # ---- MaintenanceNotificationPartner ----

    async def list_maintenancenotificationpartner(
        filter: str | None = None, select: str | None = None,
        orderby: str | None = None, top: int | None = None,
        skip: int | None = None, expand: str | None = None,
        inlinecount: str | None = None,
    ) -> str:
        params = _odata_params(filter, select, orderby, top, skip, expand, inlinecount)
        return _rj(await client.get(f"{NOTIF_ROOT}/MaintenanceNotificationPartner", params=params))

    async def get_maintenancenotificationpartner(
        MaintenanceNotification: str, MaintenanceNotificationPartner: str,
        PartnerFunction: str,
        select: str | None = None, expand: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"$format": "json"}
        if select: params["$select"] = select
        if expand: params["$expand"] = expand
        key = f"MaintenanceNotificationPartner(MaintenanceNotification='{MaintenanceNotification}',MaintenanceNotificationPartner='{MaintenanceNotificationPartner}',PartnerFunction='{PartnerFunction}')"
        return _rj(await client.get(f"{NOTIF_ROOT}/{key}", params=params))

    # ---- MaintNotificationItemActivity ----

    async def list_maintnotificationitemactivity(
        filter: str | None = None, select: str | None = None,
        orderby: str | None = None, top: int | None = None,
        skip: int | None = None, expand: str | None = None,
        inlinecount: str | None = None,
    ) -> str:
        params = _odata_params(filter, select, orderby, top, skip, expand, inlinecount)
        return _rj(await client.get(f"{NOTIF_ROOT}/MaintNotificationItemActivity", params=params))

    async def get_maintnotificationitemactivity(
        MaintenanceNotification: str, MaintenanceNotificationItem: str,
        MaintNotifItemActivity: str,
        select: str | None = None, expand: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"$format": "json"}
        if select: params["$select"] = select
        if expand: params["$expand"] = expand
        key = f"MaintNotificationItemActivity(MaintenanceNotification='{MaintenanceNotification}',MaintenanceNotificationItem='{MaintenanceNotificationItem}',MaintNotifItemActivity='{MaintNotifItemActivity}')"
        return _rj(await client.get(f"{NOTIF_ROOT}/{key}", params=params))

    # ---- MaintNotificationItemCause ----

    async def list_maintnotificationitemcause(
        filter: str | None = None, select: str | None = None,
        orderby: str | None = None, top: int | None = None,
        skip: int | None = None, expand: str | None = None,
        inlinecount: str | None = None,
    ) -> str:
        params = _odata_params(filter, select, orderby, top, skip, expand, inlinecount)
        return _rj(await client.get(f"{NOTIF_ROOT}/MaintNotificationItemCause", params=params))

    async def get_maintnotificationitemcause(
        MaintenanceNotification: str, MaintenanceNotificationItem: str,
        MaintNotifItemCause: str,
        select: str | None = None, expand: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"$format": "json"}
        if select: params["$select"] = select
        if expand: params["$expand"] = expand
        key = f"MaintNotificationItemCause(MaintenanceNotification='{MaintenanceNotification}',MaintenanceNotificationItem='{MaintenanceNotificationItem}',MaintNotifItemCause='{MaintNotifItemCause}')"
        return _rj(await client.get(f"{NOTIF_ROOT}/{key}", params=params))

    # ---- Navigation: to_FailureEffect, to_Item, to_Partner ----

    async def get_to_failureeffect(
        MaintenanceNotification: str,
        select: str | None = None, expand: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"$format": "json"}
        if select: params["$select"] = select
        if expand: params["$expand"] = expand
        return _rj(await client.get(
            f"{NOTIF_ROOT}/MaintenanceNotification('{MaintenanceNotification}')/to_FailureEffect",
            params=params,
        ))

    async def list_to_item(
        MaintenanceNotification: str,
        filter: str | None = None, select: str | None = None,
        orderby: str | None = None, top: int | None = None,
        skip: int | None = None, expand: str | None = None,
        inlinecount: str | None = None,
    ) -> str:
        params = _odata_params(filter, select, orderby, top, skip, expand, inlinecount)
        return _rj(await client.get(
            f"{NOTIF_ROOT}/MaintenanceNotification('{MaintenanceNotification}')/to_Item",
            params=params,
        ))

    async def list_to_partner(
        MaintenanceNotification: str,
        filter: str | None = None, select: str | None = None,
        orderby: str | None = None, top: int | None = None,
        skip: int | None = None, expand: str | None = None,
        inlinecount: str | None = None,
    ) -> str:
        params = _odata_params(filter, select, orderby, top, skip, expand, inlinecount)
        return _rj(await client.get(
            f"{NOTIF_ROOT}/MaintenanceNotification('{MaintenanceNotification}')/to_Partner",
            params=params,
        ))

    # ---- OData function imports ----

    async def function_approvemaintworkrequest(MaintenanceNotification: str) -> str:
        result = await client.function_import(
            NOTIF_ROOT, "ApproveMaintWorkRequest",
            params={"MaintenanceNotification": f"'{MaintenanceNotification}'"},
        )
        return _rj(result)

    async def function_completemaintnotification(MaintenanceNotification: str) -> str:
        result = await client.function_import(
            NOTIF_ROOT, "CompleteMaintNotification",
            params={"MaintenanceNotification": f"'{MaintenanceNotification}'"},
        )
        return _rj(result)

    async def function_rejectmaintworkrequest(
        MaintenanceNotification: str,
        MaintNotifLongTextForRejection: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"MaintenanceNotification": f"'{MaintenanceNotification}'"}
        if MaintNotifLongTextForRejection:
            params["MaintNotifLongTextForRejection"] = f"'{MaintNotifLongTextForRejection}'"
        result = await client.function_import(NOTIF_ROOT, "RejectMaintWorkRequest", params=params)
        return _rj(result)

    async def function_setmaintnotiftoinforequired(MaintenanceNotification: str) -> str:
        result = await client.function_import(
            NOTIF_ROOT, "SetMaintNotifToInfoRequired",
            params={"MaintenanceNotification": f"'{MaintenanceNotification}'"},
        )
        return _rj(result)

    async def function_setmaintnotiftoinprocess(MaintenanceNotification: str) -> str:
        result = await client.function_import(
            NOTIF_ROOT, "SetMaintNotifToInProcess",
            params={"MaintenanceNotification": f"'{MaintenanceNotification}'"},
        )
        return _rj(result)

    # ---- Equipment ----

    async def list_equipment(
        filter: str | None = None, select: str | None = None,
        orderby: str | None = None, top: int | None = None,
        skip: int | None = None, expand: str | None = None,
        inlinecount: str | None = None,
    ) -> str:
        params = _odata_params(filter, select, orderby, top, skip, expand, inlinecount)
        return _rj(await client.get(f"{EQUIP_ROOT}/Equipment", params=params))

    async def get_equipment(
        Equipment: str,
        select: str | None = None, expand: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"$format": "json"}
        if select: params["$select"] = select
        if expand: params["$expand"] = expand
        return _rj(await client.get(f"{EQUIP_ROOT}/Equipment('{Equipment}')", params=params))

    async def count_equipment(filter: str | None = None) -> str:
        params: dict[str, Any] = {}
        if filter: params["$filter"] = filter
        return _rj(await client.get(f"{EQUIP_ROOT}/Equipment/$count", params=params))

    async def list_equipmentlongtext(
        filter: str | None = None, select: str | None = None,
        orderby: str | None = None, top: int | None = None,
        skip: int | None = None, expand: str | None = None,
        inlinecount: str | None = None,
    ) -> str:
        params = _odata_params(filter, select, orderby, top, skip, expand, inlinecount)
        return _rj(await client.get(f"{EQUIP_ROOT}/EquipmentLongText", params=params))

    async def get_equipmentlongtext(
        Equipment: str, Language: str,
        select: str | None = None, expand: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"$format": "json"}
        if select: params["$select"] = select
        if expand: params["$expand"] = expand
        return _rj(await client.get(
            f"{EQUIP_ROOT}/EquipmentLongText(Equipment='{Equipment}',Language='{Language}')",
            params=params,
        ))

    async def list_equipmentwarranty(
        filter: str | None = None, select: str | None = None,
        orderby: str | None = None, top: int | None = None,
        skip: int | None = None, expand: str | None = None,
        inlinecount: str | None = None,
    ) -> str:
        params = _odata_params(filter, select, orderby, top, skip, expand, inlinecount)
        return _rj(await client.get(f"{EQUIP_ROOT}/EquipmentWarranty", params=params))

    async def get_equipmentwarranty(
        Equipment: str, WarrantyType: str,
        select: str | None = None, expand: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"$format": "json"}
        if select: params["$select"] = select
        if expand: params["$expand"] = expand
        return _rj(await client.get(
            f"{EQUIP_ROOT}/EquipmentWarranty(Equipment='{Equipment}',WarrantyType='{WarrantyType}')",
            params=params,
        ))

    async def get_to_longtext_in_equipment(
        Equipment: str,
        select: str | None = None, expand: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"$format": "json"}
        if select: params["$select"] = select
        if expand: params["$expand"] = expand
        return _rj(await client.get(
            f"{EQUIP_ROOT}/Equipment('{Equipment}')/to_LongText", params=params,
        ))

    # ---- FunctionalLocation ----

    async def list_functionallocation(
        filter: str | None = None, select: str | None = None,
        orderby: str | None = None, top: int | None = None,
        skip: int | None = None, expand: str | None = None,
        inlinecount: str | None = None,
    ) -> str:
        params = _odata_params(filter, select, orderby, top, skip, expand, inlinecount)
        return _rj(await client.get(f"{FLOC_ROOT}/FunctionalLocation", params=params))

    async def get_functionallocation(
        FunctionalLocation: str,
        select: str | None = None, expand: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"$format": "json"}
        if select: params["$select"] = select
        if expand: params["$expand"] = expand
        return _rj(await client.get(
            f"{FLOC_ROOT}/FunctionalLocation('{FunctionalLocation}')", params=params,
        ))

    async def count_functionallocation(filter: str | None = None) -> str:
        params: dict[str, Any] = {}
        if filter: params["$filter"] = filter
        return _rj(await client.get(f"{FLOC_ROOT}/FunctionalLocation/$count", params=params))

    async def list_functionallocationlongtext(
        filter: str | None = None, select: str | None = None,
        orderby: str | None = None, top: int | None = None,
        skip: int | None = None, expand: str | None = None,
        inlinecount: str | None = None,
    ) -> str:
        params = _odata_params(filter, select, orderby, top, skip, expand, inlinecount)
        return _rj(await client.get(f"{FLOC_ROOT}/FunctionalLocationLongText", params=params))

    async def get_functionallocationlongtext(
        FunctionalLocation: str, Language: str,
        select: str | None = None, expand: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"$format": "json"}
        if select: params["$select"] = select
        if expand: params["$expand"] = expand
        return _rj(await client.get(
            f"{FLOC_ROOT}/FunctionalLocationLongText(FunctionalLocation='{FunctionalLocation}',Language='{Language}')",
            params=params,
        ))

    async def get_to_longtext_in_functionallocation(
        FunctionalLocation: str,
        select: str | None = None, expand: str | None = None,
    ) -> str:
        params: dict[str, Any] = {"$format": "json"}
        if select: params["$select"] = select
        if expand: params["$expand"] = expand
        return _rj(await client.get(
            f"{FLOC_ROOT}/FunctionalLocation('{FunctionalLocation}')/to_LongText",
            params=params,
        ))

    # ---- Assemble tool list ----

    return [
        # MaintenanceNotification
        StructuredTool(name="list_maintenancenotification_for_cds_api_maintnotification",
            description="Retrieve a list of MaintenanceNotification entities. Supports $filter, $select, $orderby, $top (max 100), $skip, $expand, $inlinecount.",
            args_schema=ODataListInput, coroutine=list_maintenancenotification, handle_tool_error=True),
        StructuredTool(name="get_maintenancenotification_for_cds_api_maintnotification",
            description="Retrieve a single MaintenanceNotification by its notification number.",
            args_schema=GetNotifInput, coroutine=get_maintenancenotification, handle_tool_error=True),
        StructuredTool(name="count_maintenancenotification_for_cds_api_maintnotification",
            description="Get the total count of MaintenanceNotification entities matching a $filter.",
            args_schema=type("CountInput", (BaseModel,), {"filter": (Optional[str], Field(default=None, description="OData $filter expression"))}),
            coroutine=count_maintenancenotification, handle_tool_error=True),

        # MaintNotificationEffectCode
        StructuredTool(name="list_maintnotificationeffectcode_for_cds_api_maintnotification",
            description="Retrieve a list of MaintNotificationEffectCode entities.",
            args_schema=ODataListInput, coroutine=list_maintnotificationeffectcode, handle_tool_error=True),
        StructuredTool(name="get_maintnotificationeffectcode_for_cds_api_maintnotification",
            description="Retrieve a single MaintNotificationEffectCode by its key.",
            args_schema=GetEffectCodeInput, coroutine=get_maintnotificationeffectcode, handle_tool_error=True),

        # MaintenanceNotificationItem
        StructuredTool(name="list_maintenancenotificationitem_for_cds_api_maintnotification",
            description="Retrieve a list of MaintenanceNotificationItem entities.",
            args_schema=ODataListInput, coroutine=list_maintenancenotificationitem, handle_tool_error=True),
        StructuredTool(name="get_maintenancenotificationitem_for_cds_api_maintnotification",
            description="Retrieve a single MaintenanceNotificationItem by notification number and item number.",
            args_schema=GetNotifItemInput, coroutine=get_maintenancenotificationitem, handle_tool_error=True),
        StructuredTool(name="count_maintenancenotificationitem_for_cds_api_maintnotification",
            description="Get the total count of MaintenanceNotificationItem entities matching a $filter.",
            args_schema=type("CountInput2", (BaseModel,), {"filter": (Optional[str], Field(default=None, description="OData $filter expression"))}),
            coroutine=count_maintenancenotificationitem, handle_tool_error=True),

        # MaintenanceNotificationPartner
        StructuredTool(name="list_maintenancenotificationpartner",
            description="Retrieve a list of MaintenanceNotificationPartner entities.",
            args_schema=ODataListInput, coroutine=list_maintenancenotificationpartner, handle_tool_error=True),
        StructuredTool(name="get_maintenancenotificationpartner_for_cds_api_maintnotification",
            description="Retrieve a single MaintenanceNotificationPartner by notification, partner counter, and function.",
            args_schema=GetNotifPartnerInput, coroutine=get_maintenancenotificationpartner, handle_tool_error=True),

        # MaintNotificationItemActivity
        StructuredTool(name="list_maintnotificationitemactivity_for_cds_api_maintnotification",
            description="Retrieve a list of MaintNotificationItemActivity entities.",
            args_schema=ODataListInput, coroutine=list_maintnotificationitemactivity, handle_tool_error=True),
        StructuredTool(name="get_maintnotificationitemactivity_for_cds_api_maintnotification",
            description="Retrieve a single MaintNotificationItemActivity by notification, item, and activity counter.",
            args_schema=GetNotifItemActivityInput, coroutine=get_maintnotificationitemactivity, handle_tool_error=True),

        # MaintNotificationItemCause
        StructuredTool(name="list_maintnotificationitemcause_for_cds_api_maintnotification",
            description="Retrieve a list of MaintNotificationItemCause entities.",
            args_schema=ODataListInput, coroutine=list_maintnotificationitemcause, handle_tool_error=True),
        StructuredTool(name="get_maintnotificationitemcause_for_cds_api_maintnotification",
            description="Retrieve a single MaintNotificationItemCause by notification, item, and cause counter.",
            args_schema=GetNotifItemCauseInput, coroutine=get_maintnotificationitemcause, handle_tool_error=True),

        # Navigation
        StructuredTool(name="get_to_failureeffect_in_maintenancenotification",
            description="Navigate from a MaintenanceNotification to its related FailureEffect entity.",
            args_schema=type("NavInput1", (BaseModel,), {
                "MaintenanceNotification": (str, Field(description="Maintenance Notification number")),
                "select": (Optional[str], Field(default=None, description="$select")),
                "expand": (Optional[str], Field(default=None, description="$expand")),
            }),
            coroutine=get_to_failureeffect, handle_tool_error=True),
        StructuredTool(name="list_to_item_in_maintenancenotification",
            description="Navigate from a MaintenanceNotification to its related Item entities.",
            args_schema=ListNotifByNavInput, coroutine=list_to_item, handle_tool_error=True),
        StructuredTool(name="list_to_partner_in_maintenancenotification",
            description="Navigate from a MaintenanceNotification to its related Partner entities.",
            args_schema=ListNotifByNavInput, coroutine=list_to_partner, handle_tool_error=True),

        # Function imports
        StructuredTool(name="function_approvemaintworkrequest_for_cds_api_maintnotification",
            description="Approve a maintenance work request (notification). Only call after explicit user confirmation.",
            args_schema=ApproveMaintWorkRequestInput, coroutine=function_approvemaintworkrequest, handle_tool_error=True),
        StructuredTool(name="function_completemaintnotification_for_cds_api_maintnotification",
            description="Complete a maintenance notification. Only call after explicit user confirmation.",
            args_schema=CompleteMaintNotificationInput, coroutine=function_completemaintnotification, handle_tool_error=True),
        StructuredTool(name="function_rejectmaintworkrequest_for_cds_api_maintnotification",
            description="Reject a maintenance work request (notification). Only call after explicit user confirmation.",
            args_schema=RejectMaintWorkRequestInput, coroutine=function_rejectmaintworkrequest, handle_tool_error=True),
        StructuredTool(name="function_setmaintnotiftoinforequired",
            description="Set a maintenance notification status to 'Information Required'. Only call after explicit user confirmation.",
            args_schema=SetMaintNotifToInfoRequiredInput, coroutine=function_setmaintnotiftoinforequired, handle_tool_error=True),
        StructuredTool(name="function_setmaintnotiftoinprocess_for_cds_api_maintnotification",
            description="Set a maintenance notification status to 'In Process'. Only call after explicit user confirmation.",
            args_schema=SetMaintNotifToInProcessInput, coroutine=function_setmaintnotiftoinprocess, handle_tool_error=True),

        # Equipment
        StructuredTool(name="list_equipment_for_cds_api_equipment",
            description="Retrieve a list of Equipment entities from SAP.",
            args_schema=ODataListInput, coroutine=list_equipment, handle_tool_error=True),
        StructuredTool(name="get_equipment_for_cds_api_equipment",
            description="Retrieve a single Equipment entity by equipment number.",
            args_schema=GetEquipmentInput, coroutine=get_equipment, handle_tool_error=True),
        StructuredTool(name="count_equipment_for_cds_api_equipment",
            description="Get the total count of Equipment entities matching a $filter.",
            args_schema=type("CountInput3", (BaseModel,), {"filter": (Optional[str], Field(default=None, description="OData $filter expression"))}),
            coroutine=count_equipment, handle_tool_error=True),
        StructuredTool(name="list_equipmentlongtext_for_cds_api_equipment",
            description="Retrieve a list of EquipmentLongText entities.",
            args_schema=ODataListInput, coroutine=list_equipmentlongtext, handle_tool_error=True),
        StructuredTool(name="get_equipmentlongtext_for_cds_api_equipment",
            description="Retrieve a single EquipmentLongText by equipment number and language key.",
            args_schema=type("GetEquipLongText", (BaseModel,), {
                "Equipment": (str, Field(description="Equipment number")),
                "Language": (str, Field(description="Language key e.g. EN")),
                "select": (Optional[str], Field(default=None, description="$select")),
                "expand": (Optional[str], Field(default=None, description="$expand")),
            }),
            coroutine=get_equipmentlongtext, handle_tool_error=True),
        StructuredTool(name="list_equipmentwarranty_for_cds_api_equipment",
            description="Retrieve a list of EquipmentWarranty entities.",
            args_schema=ODataListInput, coroutine=list_equipmentwarranty, handle_tool_error=True),
        StructuredTool(name="get_equipmentwarranty_for_cds_api_equipment",
            description="Retrieve a single EquipmentWarranty by equipment number and warranty type.",
            args_schema=type("GetEquipWarranty", (BaseModel,), {
                "Equipment": (str, Field(description="Equipment number")),
                "WarrantyType": (str, Field(description="Warranty type key")),
                "select": (Optional[str], Field(default=None, description="$select")),
                "expand": (Optional[str], Field(default=None, description="$expand")),
            }),
            coroutine=get_equipmentwarranty, handle_tool_error=True),
        StructuredTool(name="get_to_longtext_in_equipment_for_cds_api_equipment",
            description="Navigate from an Equipment entity to its LongText.",
            args_schema=type("NavEquipLongText", (BaseModel,), {
                "Equipment": (str, Field(description="Equipment number")),
                "select": (Optional[str], Field(default=None, description="$select")),
                "expand": (Optional[str], Field(default=None, description="$expand")),
            }),
            coroutine=get_to_longtext_in_equipment, handle_tool_error=True),

        # FunctionalLocation
        StructuredTool(name="list_functionallocation_for_cds_api_functionallocation",
            description="Retrieve a list of FunctionalLocation entities from SAP.",
            args_schema=ODataListInput, coroutine=list_functionallocation, handle_tool_error=True),
        StructuredTool(name="get_functionallocation_for_cds_api_functionallocation",
            description="Retrieve a single FunctionalLocation entity by its identifier.",
            args_schema=GetFlocInput, coroutine=get_functionallocation, handle_tool_error=True),
        StructuredTool(name="count_functionallocation_for_cds_api_functionallocation",
            description="Get the total count of FunctionalLocation entities matching a $filter.",
            args_schema=type("CountInput4", (BaseModel,), {"filter": (Optional[str], Field(default=None, description="OData $filter expression"))}),
            coroutine=count_functionallocation, handle_tool_error=True),
        StructuredTool(name="list_functionallocationlongtext_for_cds_api_functionallocation",
            description="Retrieve a list of FunctionalLocationLongText entities.",
            args_schema=ODataListInput, coroutine=list_functionallocationlongtext, handle_tool_error=True),
        StructuredTool(name="get_functionallocationlongtext_for_cds_api_functionallocation",
            description="Retrieve a single FunctionalLocationLongText by location and language.",
            args_schema=GetFlocLongtextInput, coroutine=get_functionallocationlongtext, handle_tool_error=True),
        StructuredTool(name="get_to_longtext_in_functionallocation",
            description="Navigate from a FunctionalLocation entity to its LongText.",
            args_schema=type("NavFlocLongText", (BaseModel,), {
                "FunctionalLocation": (str, Field(description="Functional Location identifier")),
                "select": (Optional[str], Field(default=None, description="$select")),
                "expand": (Optional[str], Field(default=None, description="$expand")),
            }),
            coroutine=get_to_longtext_in_functionallocation, handle_tool_error=True),
    ]

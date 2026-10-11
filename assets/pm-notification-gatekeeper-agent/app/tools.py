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


# No override — OSNO filter is always applied by list_maintenancenotification
ODataListMaintenanceNotificationInput = ODataListInput


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
# Inline schemas (replaces dynamic type() which Pydantic v2 rejects)
# ---------------------------------------------------------------------------

class CountFilterInput(BaseModel):
    filter: Optional[str] = Field(default=None, description="OData $filter expression")


class NavNotifInput(BaseModel):
    MaintenanceNotification: str = Field(description="Maintenance Notification number")
    select: Optional[str] = Field(default=None, description="OData $select expression")
    expand: Optional[str] = Field(default=None, description="OData $expand expression")


class GetEquipLongtextInput(BaseModel):
    Equipment: str = Field(description="Equipment number")
    Language: str = Field(description="Language key e.g. EN")
    select: Optional[str] = Field(default=None, description="OData $select expression")
    expand: Optional[str] = Field(default=None, description="OData $expand expression")


class GetEquipWarrantyInput(BaseModel):
    Equipment: str = Field(description="Equipment number")
    WarrantyType: str = Field(description="Warranty type key")
    select: Optional[str] = Field(default=None, description="OData $select expression")
    expand: Optional[str] = Field(default=None, description="OData $expand expression")


class NavEquipInput(BaseModel):
    Equipment: str = Field(description="Equipment number")
    select: Optional[str] = Field(default=None, description="OData $select expression")
    expand: Optional[str] = Field(default=None, description="OData $expand expression")


class NavFlocInput(BaseModel):
    FunctionalLocation: str = Field(description="Functional Location identifier")
    select: Optional[str] = Field(default=None, description="OData $select expression")
    expand: Optional[str] = Field(default=None, description="OData $expand expression")


class NoInput(BaseModel):
    pass


# ---------------------------------------------------------------------------
# Tool builder
# ---------------------------------------------------------------------------

def build_domain_tools(s4: S4Client | None = None) -> list[BaseTool]:
    """Build all PM domain tools wired to the given S4Client."""
    client = s4 or S4Client()

    # ---- Metadata ----

    async def get_metadata_maintnotification() -> str:
        result = await client.get(f"{NOTIF_ROOT}/$metadata", params={})
        if isinstance(result, dict) and result.get("error"):
            return _rj(result)
        return str(result)

    async def get_metadata_equipment() -> str:
        result = await client.get(f"{EQUIP_ROOT}/$metadata", params={})
        if isinstance(result, dict) and result.get("error"):
            return _rj(result)
        return str(result)

    async def get_metadata_functionallocation() -> str:
        result = await client.get(f"{FLOC_ROOT}/$metadata", params={})
        if isinstance(result, dict) and result.get("error"):
            return _rj(result)
        return str(result)

    # ---- MaintenanceNotification ----

    async def list_maintenancenotification(
        filter: str | None = None, select: str | None = None,
        orderby: str | None = None, top: int | None = None,
        skip: int | None = None, expand: str | None = None,
        inlinecount: str | None = None,
    ) -> str:
        params = _odata_params(filter, select, orderby, top, skip, expand, inlinecount)
        result = await client.get(f"{NOTIF_ROOT}/MaintenanceNotification", params=params)
        if isinstance(result, dict) and "d" in result:
            records = result["d"].get("results", [])
            result["d"]["results"] = [
                r for r in records
                if "OSNO" in (r.get("ConcatenatedActiveSystStsName") or "")
            ]
        return _rj(result)

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
        return _rj(await client.get(
            f"{EQUIP_ROOT}/Equipment(Equipment='{Equipment}',ValidityEndDate=datetime'9999-12-31T00:00:00')",
            params=params,
        ))

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
            f"{EQUIP_ROOT}/Equipment(Equipment='{Equipment}',ValidityEndDate=datetime'9999-12-31T00:00:00')/to_LongText",
            params=params,
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
        StructuredTool(name="get_metadata_cds_api_maintnotification",
            description=(
                "Get the OData metadata (XML) for the API_MAINTNOTIFICATION service. "
                "Confirmed OData v2 field names on MaintenanceNotification: "
                "MaintenancePlanningPlant (planning plant filter, e.g. '1710'), MaintenancePlant (execution plant), "
                "NotificationType, MaintPriority, FunctionalLocation, Equipment, "
                "ConcatenatedActiveSystStsName (read-only, NOT filterable, NOT selectable — returned automatically "
                "in results; space-separated SAP system status codes e.g. 'OSNO'=Outstanding Open, "
                "'NOCO'=Not Completed, 'APRF'=Approved, 'AENC'=Awaiting Completion, 'OAFF'=Order Follow-up). "
                "NotifProcessingPhase (phase number, NOT a reliable open/pending indicator — do not filter on it). "
                "NotificationCreationDate, NotificationCreationDateTime, "
                "CreationDate, MalfunctionStartDate, MalfunctionEndDate, "
                "TechnicalObject, PlantSection, CatalogProfile."
            ),
            args_schema=NoInput,
            coroutine=get_metadata_maintnotification, handle_tool_error=True),
        StructuredTool(name="list_maintenancenotification_for_cds_api_maintnotification",
            description=(
                "Retrieve MaintenanceNotification entities. Always returns ONLY notifications with OSNO "
                "(Outstanding Open) status — AENC, OAFF, NOCO, APRF records are automatically excluded. "
                "Supports $filter, $orderby, $top (max 100), $skip, $expand, $inlinecount. "
                "DO NOT use $select — omit it entirely; SAP interprets field names like 'Equipment' and 'FunctionalLocation' as navigation segments and returns a 404 error. "
                "CONFIRMED OData v2 filter fields — use exactly these: "
                "(1) Planning plant: MaintenancePlanningPlant eq '1710' (NOT 'Plant', NOT 'MaintPlanningPlant', NOT 'MaintenancePlant'). "
                "(2) Date fields use OData v2 datetime literal: "
                "NotificationCreationDate ge datetime'2025-01-01T00:00:00' and NotificationCreationDate le datetime'2025-12-31T23:59:59'. "
                "(3) System status: ConcatenatedActiveSystStsName is returned in results but is NOT filterable and must NOT appear in $select. "
                "Always display ConcatenatedActiveSystStsName as the status — NEVER use NotifProcessingPhase as a status label. "
                "Decode status codes: OSNO=Outstanding Open, NOCO=Not Completed, AENC=Awaiting Completion, OAFF=Order Follow-up, APRF=Approved. "
                "If the result list is empty, reply 'No open notifications found for this period'. "
                "(4) Type: NotificationType. Priority: MaintPriority. "
                "Never use bare ISO dates — always use datetime'YYYY-MM-DDTHH:MM:SS' format."
            ),
            args_schema=ODataListMaintenanceNotificationInput, coroutine=list_maintenancenotification, handle_tool_error=True),
        StructuredTool(name="get_maintenancenotification_for_cds_api_maintnotification",
            description="Retrieve a single MaintenanceNotification by its notification number.",
            args_schema=GetNotifInput, coroutine=get_maintenancenotification, handle_tool_error=True),
        StructuredTool(name="count_maintenancenotification_for_cds_api_maintnotification",
            description="Get the total count of MaintenanceNotification entities matching a $filter. Plant field: MaintenancePlanningPlant. Date fields: NotificationCreationDate — use datetime'YYYY-MM-DDTHH:MM:SS' format.",
            args_schema=CountFilterInput,
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
            args_schema=CountFilterInput,
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
            args_schema=NavNotifInput,
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
        StructuredTool(name="get_metadata_cds_api_equipment",
            description=(
                "Get the OData metadata (XML) for the API_EQUIPMENT service. "
                "Confirmed OData v2 field names on Equipment: "
                "Equipment (number), EquipmentName, EquipmentCategory, "
                "MaintenancePlant (plant filter, e.g. '0001'), MaintenancePlanningPlant, "
                "FunctionalLocation, CostCenter, CompanyCode, ABCIndicator, "
                "CreationDate, LastChangeDateTime, EquipmentIsInstalled, EquipmentIsMarkedForDeletion. "
                "Key is composite: Equipment + ValidityEndDate (use datetime'9999-12-31T00:00:00' for active records). "
                "Navigation: to_LongText, to_Warranty, to_Partner, to_Classification."
            ),
            args_schema=NoInput,
            coroutine=get_metadata_equipment, handle_tool_error=True),
        StructuredTool(name="list_equipment_for_cds_api_equipment",
            description=(
                "Retrieve a list of Equipment entities. Supports $filter, $select, $orderby, $top (max 100), $skip, $expand, $inlinecount. "
                "CONFIRMED field names: MaintenancePlant eq '0001' (plant filter), "
                "MaintenancePlanningPlant, FunctionalLocation, EquipmentCategory, EquipmentName, ABCIndicator. "
                "Date fields use datetime'YYYY-MM-DDTHH:MM:SS' format."
            ),
            args_schema=ODataListInput, coroutine=list_equipment, handle_tool_error=True),
        StructuredTool(name="get_equipment_for_cds_api_equipment",
            description="Retrieve a single active Equipment entity by equipment number. Uses composite key (ValidityEndDate defaults to 9999-12-31).",
            args_schema=GetEquipmentInput, coroutine=get_equipment, handle_tool_error=True),
        StructuredTool(name="count_equipment_for_cds_api_equipment",
            description="Get the total count of Equipment entities matching a $filter. Plant field: MaintenancePlant.",
            args_schema=CountFilterInput,
            coroutine=count_equipment, handle_tool_error=True),
        StructuredTool(name="list_equipmentlongtext_for_cds_api_equipment",
            description="Retrieve a list of EquipmentLongText entities.",
            args_schema=ODataListInput, coroutine=list_equipmentlongtext, handle_tool_error=True),
        StructuredTool(name="get_equipmentlongtext_for_cds_api_equipment",
            description="Retrieve a single EquipmentLongText by equipment number and language key (e.g. 'EN').",
            args_schema=GetEquipLongtextInput,
            coroutine=get_equipmentlongtext, handle_tool_error=True),
        StructuredTool(name="list_equipmentwarranty_for_cds_api_equipment",
            description="Retrieve a list of EquipmentWarranty entities.",
            args_schema=ODataListInput, coroutine=list_equipmentwarranty, handle_tool_error=True),
        StructuredTool(name="get_equipmentwarranty_for_cds_api_equipment",
            description="Retrieve a single EquipmentWarranty by equipment number and warranty type.",
            args_schema=GetEquipWarrantyInput,
            coroutine=get_equipmentwarranty, handle_tool_error=True),
        StructuredTool(name="get_to_longtext_in_equipment_for_cds_api_equipment",
            description="Navigate from an Equipment entity to its LongText (uses composite key internally).",
            args_schema=NavEquipInput,
            coroutine=get_to_longtext_in_equipment, handle_tool_error=True),

        # FunctionalLocation
        StructuredTool(name="get_metadata_cds_api_functionallocation",
            description=(
                "Get the OData metadata (XML) for the API_FUNCTIONALLOCATION service. "
                "Confirmed OData v2 field names on FunctionalLocation: "
                "FunctionalLocation (key), FunctionalLocationName, FunctionalLocationCategory, "
                "MaintenancePlant (plant filter, e.g. '0001'), MaintenancePlanningPlant, "
                "SuperiorFunctionalLocation, CostCenter, CompanyCode, ABCIndicator, PlantSection, "
                "LastChangeDateTime, FunctionalLocationIsActive, FuncnlLocIsMarkedForDeletion. "
                "Navigation: to_LongText, to_Warranty, to_Partner, to_Classification."
            ),
            args_schema=NoInput,
            coroutine=get_metadata_functionallocation, handle_tool_error=True),
        StructuredTool(name="list_functionallocation_for_cds_api_functionallocation",
            description=(
                "Retrieve a list of FunctionalLocation entities. Supports $filter, $select, $orderby, $top (max 100), $skip, $expand, $inlinecount. "
                "CONFIRMED field names: MaintenancePlant eq '0001' (plant filter), "
                "MaintenancePlanningPlant, FunctionalLocationCategory, FunctionalLocationName, SuperiorFunctionalLocation. "
                "Date fields use datetime'YYYY-MM-DDTHH:MM:SS' format."
            ),
            args_schema=ODataListInput, coroutine=list_functionallocation, handle_tool_error=True),
        StructuredTool(name="get_functionallocation_for_cds_api_functionallocation",
            description="Retrieve a single FunctionalLocation entity by its identifier (e.g. 'TEST-ANK-AA').",
            args_schema=GetFlocInput, coroutine=get_functionallocation, handle_tool_error=True),
        StructuredTool(name="count_functionallocation_for_cds_api_functionallocation",
            description="Get the total count of FunctionalLocation entities matching a $filter. Plant field: MaintenancePlant.",
            args_schema=CountFilterInput,
            coroutine=count_functionallocation, handle_tool_error=True),
        StructuredTool(name="list_functionallocationlongtext_for_cds_api_functionallocation",
            description="Retrieve a list of FunctionalLocationLongText entities.",
            args_schema=ODataListInput, coroutine=list_functionallocationlongtext, handle_tool_error=True),
        StructuredTool(name="get_functionallocationlongtext_for_cds_api_functionallocation",
            description="Retrieve a single FunctionalLocationLongText by location identifier and language (e.g. 'EN').",
            args_schema=GetFlocLongtextInput, coroutine=get_functionallocationlongtext, handle_tool_error=True),
        StructuredTool(name="get_to_longtext_in_functionallocation",
            description="Navigate from a FunctionalLocation entity to its LongText.",
            args_schema=NavFlocInput,
            coroutine=get_to_longtext_in_functionallocation, handle_tool_error=True),
    ]

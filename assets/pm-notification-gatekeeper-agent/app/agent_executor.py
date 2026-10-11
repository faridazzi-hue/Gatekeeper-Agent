import logging
import os

from a2a.server.agent_execution import AgentExecutor as A2AAgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError
from opentelemetry import trace

from agent import SampleAgent
from load_skill_resources import get_load_skill_resource_tool
from prompt_injection_detector import wrap_tool

# CF mode: direct OData via BTP Destination Service (no user JWT needed)
# Joule mode: Agent Gateway with per-user JWT OBO
_IS_CF = bool(os.environ.get("VCAP_SERVICES"))

if _IS_CF:
    from tools import build_domain_tools
else:
    from mcp_providers.agw import get_mcp_tools

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class AgentExecutor(A2AAgentExecutor):
    def __init__(self):
        self.agent = SampleAgent()
        self.skill_tools = get_load_skill_resource_tool()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent and stream results back via A2A protocol.

        On CF: loads domain tools directly via BTP Destination Service (technical user).
        On Joule: discovers MCP tools from Agent Gateway using per-user JWT.
        Business milestones are instrumented with structured logs and OTel spans.

        Args:
            context: Request context containing user input and task info
            event_queue: Queue for publishing task status updates

        Raises:
            ServerError: On unrecoverable agent execution errors
        """
        query = context.get_user_input()
        task = context.current_task
        if not task:
            assert context.message is not None, "Cannot create task without a message"
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        sap_tools: list = []
        sap_tools_available = False

        if _IS_CF:
            # CF: direct OData — always available, no user JWT required
            sap_tools = build_domain_tools()
            sap_tools_available = True
            logger.info(
                "CF mode: loaded %d domain tool(s): %s",
                len(sap_tools),
                [t.name for t in sap_tools],
            )
        else:
            # Joule: Agent Gateway — user token is read from context var set by JWTContextMiddleware
            try:
                sap_tools = await get_mcp_tools()
                if not sap_tools:
                    logger.warning("No tools returned from Agent Gateway")
                else:
                    sap_tools_available = True
                    logger.info(
                        "Loaded %d MCP tool(s) for agent execution: %s",
                        len(sap_tools),
                        [t.name for t in sap_tools],
                    )
            except Exception as e:
                logger.error("Failed to load tools from Agent Gateway: %s", e)

        tools = [*sap_tools, *self.skill_tools]

        # Wrap all tools with prompt injection scanning for uniform protection
        tools = [wrap_tool(t) for t in tools]

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        try:
            await self._run_agent(query, task, tools, updater, sap_tools_available=sap_tools_available)
        except Exception as e:
            logger.exception("Agent execution error")
            raise ServerError(error=InternalError()) from e

    async def _run_agent(self, query: str, task, tools, updater: TaskUpdater, *, sap_tools_available: bool = True) -> None:
        """Run the agent stream and handle business milestone instrumentation.

        Business logic is extracted from execute() into this plain async method
        so OTel spans can be used as context managers without GeneratorExit errors.
        """
        with tracer.start_as_current_span("pm-gatekeeper.agent-execution") as span:
            span.set_attribute("task.id", task.id)
            span.set_attribute("tool.count", len(tools))

            async for item in self.agent.stream(query, task.context_id, tools=tools, sap_tools_available=sap_tools_available):
                is_task_complete = item["is_task_complete"]
                require_user_input = item["require_user_input"]
                content = item["content"]

                if require_user_input:
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(content, task.context_id, task.id),
                        final=True,
                    )
                    break
                elif is_task_complete:
                    # M5 — SAP Action Execution and Audit
                    # Log and span are emitted by the agent's LLM reasoning layer.
                    # The executor records completion at the infrastructure level.
                    logger.info(
                        "M5.achieved: agent execution complete for task %s", task.id
                    )
                    span.set_attribute("task.complete", True)
                    await updater.add_artifact(
                        [Part(root=TextPart(text=content))], name="agent_result"
                    )
                    await updater.complete()
                    break
                else:
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(content, task.context_id, task.id),
                    )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise ServerError(error=UnsupportedOperationError())

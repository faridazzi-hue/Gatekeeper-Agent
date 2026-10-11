import os
import pathlib

# Gate Joule/Kyma-specific AI Core telemetry setup.
# On CF this env var is not set, so the block is skipped.
if os.environ.get("JOULE_RUNTIME"):
    from sap_cloud_sdk.aicore import set_aicore_config
    set_aicore_config()

import logging

import click
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from sap_cloud_sdk import bootstrap
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse

from agent_executor import AgentExecutor
from mcp_providers.agw import set_user_token, reset_user_token

_CHAT_HTML = (pathlib.Path(__file__).parent / "static" / "chat.html").read_text(encoding="utf-8")


async def _chat_page(request: Request) -> HTMLResponse:
    return HTMLResponse(_CHAT_HTML)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))


class JWTContextMiddleware(BaseHTTPMiddleware):
    """Extracts JWT token from Authorization header and sets it in context."""

    async def dispatch(self, request, call_next):
        auth_header = request.headers.get("authorization", "")
        token = auth_header[7:] if auth_header.lower().startswith("bearer ") else None
        token_ctx = set_user_token(token)
        try:
            return await call_next(request)
        finally:
            reset_user_token(token_ctx)


def _build_app():
    skill = AgentSkill(
        id="pm-notification-gatekeeper-agent",
        name="pm-notification-gatekeeper-agent",
        description="An AI agent that screens SAP plant maintenance notifications for completeness, consistency, and duplicate detection, then recommends Approve, Rework, or Reject with human-in-the-loop confirmation before any SAP action is taken.",
        tags=["plant", "maintenance", "notification", "gatekeeper", "agent"],
        examples=[
            "Show me the pending maintenance notifications for plant 1710",
            "Review notification 10000123 and give me your recommendation",
        ],
    )
    agent_card = AgentCard(
        name="pm-notification-gatekeeper-agent",
        description="An AI agent that screens SAP plant maintenance notifications for completeness, consistency, and duplicate detection, then recommends Approve, Rework, or Reject with human-in-the-loop confirmation before any SAP action is taken.",
        url=os.environ.get("AGENT_PUBLIC_URL", f"http://{HOST}:{PORT}/"),
        version="1.0.0",
        default_input_modes=["text", "text/plain"],
        default_output_modes=["text", "text/plain"],
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        skills=[skill],
    )
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=DefaultRequestHandler(
            agent_executor=AgentExecutor(),
            task_store=InMemoryTaskStore(),
        ),
    )
    app = server.build()
    app.add_route("/chat", _chat_page, methods=["GET"])
    app.add_middleware(JWTContextMiddleware)
    try:
        bootstrap(app)
    except Exception:
        logger.warning("bootstrap() unavailable — continuing without SAP Cloud SDK telemetry")
    return app


# ASGI app exposed for gunicorn on CF:
#   gunicorn --worker-class uvicorn.workers.UvicornWorker ... --chdir app main:application
application = _build_app()


@click.command()
@click.option("--host", default=HOST)
@click.option("--port", default=PORT)
def main(host: str, port: int):
    logger.info(f"Starting A2A server at http://{host}:{port}")
    uvicorn.run(application, host=host, port=port)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter  # type: ignore[call-arg]

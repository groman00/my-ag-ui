import os
import uvicorn
from ag_ui.core import RunAgentInput
from fastapi import FastAPI
from http import HTTPStatus
from fastapi.requests import Request
from fastapi.responses import Response, StreamingResponse
from pydantic import ValidationError
import json

from pydantic_ai import Agent
from pydantic_ai.ag_ui import run_ag_ui, SSE_CONTENT_TYPE
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from .config import settings

provider = GoogleProvider(api_key=settings.gemini_api_key)
model = GoogleModel('gemini-1.5-flash', provider=provider)
agent = Agent(model)

app = FastAPI()


@app.post("/")
async def run_agent(request: Request) -> Response:
    accept = request.headers.get('accept', SSE_CONTENT_TYPE)
    try:
        run_input = RunAgentInput.model_validate(await request.json())
    except ValidationError as e:  # pragma: no cover
        return Response(
            content=json.dumps(e.json()),
            media_type='application/json',
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    event_stream = run_ag_ui(agent, run_input, accept=accept)

    return StreamingResponse(event_stream, media_type=accept)




def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(
        "example_server:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

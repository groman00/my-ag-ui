import os
import uvicorn
from ag_ui.core import RunAgentInput
from fastapi import FastAPI
from http import HTTPStatus
from fastapi.requests import Request
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
import json
from pydantic_ai import Agent
from pydantic_ai.ag_ui import run_ag_ui, SSE_CONTENT_TYPE
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from .config import settings
from .vercel_to_pydantic import (
    ChatMessageRequest,
    convert_vercel_messages_to_pydantic,
    to_data_stream_protocol,
)

provider = GoogleProvider(api_key=settings.gemini_api_key)
model = GoogleModel('gemini-1.5-flash', provider=provider)
agent = Agent(model)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# @agent.tool_plain
# def roll_dice() -> str:
#     """Roll a six-sided die and return the result."""
#     return str(random.randint(1, 6))


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




# https://github.com/mattlgroff/pydantic-ai-fastapi-react-vite-agent
# @app.post("/chat")
# async def chat(request: Request):
#     json = await request.json()
#     print("Chat request: ", json)
#     message = json['messages'][0]['parts'][0]['text']
#     async with agent.run_stream(message) as result:
#         # incomplete messages before the stream finishes
#         print(result.all_messages())

@app.post("/chat")
async def chat_with_agent(request: ChatMessageRequest) -> StreamingResponse:
    """
    The main (and only) endpoint for this minimalist demonstration.

    This shows how to host a Pydantic-AI agent in FastAPI for chat with tool calling
    using the Vercel AI SDK on the frontend. This minimalist approach focuses on the
    core concepts without authentication, conversation persistence, or other features.

    In a real application, you could add:
    - Health check endpoint (/health)
    - Conversation history endpoints (/conversations)
    - User authentication and authorization
    - Rate limiting and request validation
    - Logging and monitoring
    - Multiple agent types

    This endpoint demonstrates:
    1. Receiving Vercel AI SDK message format
    2. Converting to Pydantic-AI format
    3. Running the agent with tool calling
    4. Streaming responses back via Server-Sent Events
    5. Handling conversation history

    Example request from Vercel AI SDK:
    {
        "messages": [
            {"role": "user", "content": "What's 15 + 27?", "parts": [{"type": "text", "text": "What's 15 + 27?"}]}
        ]
    }
    """
    print(f"🚀 Received chat request with {len(request.messages)} messages")

    try:

        # Get the system prompt content as string (from the agent creation)
        system_prompt_content = """You are a helpful assistant that can convert colors to hex codes.
You can do nothing else.
"""

        # Convert Vercel AI SDK messages to Pydantic-AI format
        user_message, message_history = convert_vercel_messages_to_pydantic(
            request.messages,
            system_prompt_content=system_prompt_content
        )

        print(f"📝 User message: {user_message[:100]}...")
        print(f"📚 Message history: {len(message_history)} previous messages")

        # Create the streaming response function
        async def stream_agent_response():
            """
            This async generator function handles the streaming response.

            It runs the agent and converts the stream to the format expected
            by the Vercel AI SDK on the frontend.
            """
            try:
                # Run the agent with conversation context - matching the working pattern
                async with agent.iter(user_message, message_history=message_history) as agent_run:
                    async for node in agent_run:
                        # Convert to data stream protocol format - use the same pattern as the working version
                        async for chunk in to_data_stream_protocol(node, agent_run):
                            yield chunk

            except Exception as e:
                print(f"❌ Error in agent stream: {str(e)}")
                # Send error as a text stream
                error_id = "error-text"
                error_msg = f"I apologize, but I encountered an error: {str(e)}"

                yield f"data: {json.dumps({'type': 'text-start', 'id': error_id})}\n\n"
                yield f"data: {json.dumps({'type': 'text-delta', 'id': error_id, 'delta': error_msg})}\n\n"
                yield f"data: {json.dumps({'type': 'text-end', 'id': error_id})}\n\n"

        # Return the streaming response with proper headers
        response = StreamingResponse(
            stream_agent_response(),
            media_type="text/event-stream"
        )

        # Set headers required for Server-Sent Events
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        response.headers["Content-Type"] = "text/event-stream"

        return response

    except Exception as e:
        print(f"❌ Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(
        "example_server:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

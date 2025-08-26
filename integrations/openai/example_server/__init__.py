"""
Example server for the AG-UI protocol.
"""

import os
import uuid
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from ag_ui.core import (
    RunAgentInput,
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
)
from ag_ui.core.events import ToolCallChunkEvent, TextMessageChunkEvent
from ag_ui.encoder import EventEncoder
from openai import OpenAI
from .config import settings

app = FastAPI(title="AG-UI Endpoint")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3002"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    api_key=settings.gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

@app.post("/")
async def agentic_chat_endpoint(input_data: RunAgentInput, request: Request):
    print("Input data: ", input_data)
    # print("Request: ", request)

    """Agentic chat endpoint"""
    # Get the accept header from the request
    accept_header = request.headers.get("accept")

    # Create an event encoder to properly format SSE events
    encoder = EventEncoder(accept=accept_header)

    async def event_generator():
        try:
            # Send run started event
            yield encoder.encode(
            RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id
            ),
            )

            # Call OpenAI's API with streaming enabled
            stream = client.chat.completions.create(
                model="gemini-2.5-flash",
                stream=True,
                # Convert AG-UI tools format to OpenAI's expected format
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.parameters,
                        }
                    }
                    for tool in input_data.tools
                ] if input_data.tools else None,
                # Transform AG-UI messages to OpenAI's message format
                messages=[
                    {
                        "role": message.role,
                        "content": message.content or "",
                        # Include tool calls if this is an assistant message with tools
                        **({"tool_calls": message.tool_calls} if message.role == "assistant" and hasattr(message, 'tool_calls') and message.tool_calls else {}),
                        # Include tool call ID if this is a tool result message
                        **({"tool_call_id": message.tool_call_id} if message.role == "tool" and hasattr(message, 'tool_call_id') else {}),
                    }
                    for message in input_data.messages
                ],
            )

            message_id = str(uuid.uuid4())

            # Stream each chunk from OpenAI's response
            for chunk in stream:
                # print(chunk.choices)

                # Handle text content chunks
                if chunk.choices[0].delta.content:
                    yield encoder.encode(
                        TextMessageChunkEvent(
                            type=EventType.TEXT_MESSAGE_CHUNK,
                            message_id=message_id,
                            delta=chunk.choices[0].delta.content,
                        )
                    )
                # Handle tool call chunks
                elif chunk.choices[0].delta.tool_calls:
                    tool_call = chunk.choices[0].delta.tool_calls[0]

                    yield encoder.encode(
                        ToolCallChunkEvent(
                            type=EventType.TOOL_CALL_CHUNK,
                            tool_call_id=tool_call.id,
                            tool_call_name=tool_call.function.name if tool_call.function else None,
                            parent_message_id=message_id,
                            delta=tool_call.function.arguments if tool_call.function else None,
                        )
                    )

            yield encoder.encode(
                RunFinishedEvent(
                    type=EventType.RUN_FINISHED,
                    thread_id=input_data.thread_id,
                    run_id=input_data.run_id
                )
            )

        except Exception as error:
            yield encoder.encode(
                RunErrorEvent(
                    type=EventType.RUN_ERROR,
                    message=str(error)
                )
            )
            raise error

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type()
    )

# @app.post("/copilotkit")
# async def testing_langchain(request: Request):
#     json = await request.json()
#     print("Input data: ", json)



def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "example_server:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

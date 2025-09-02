# https://github.com/mattlgroff/pydantic-ai-fastapi-react-vite-agent/blob/master/agent-backend/main.py

"""
Minimalist FastAPI + Pydantic-AI Math Agent Server
=================================================

This single-file server demonstrates how to build an AI agent that works with the Vercel AI SDK.
It provides a /agent POST endpoint that streams responses using Server-Sent Events (SSE).

Key Concepts Demonstrated:
- FastAPI with async streaming responses
- Pydantic-AI agent with custom tools
- Vercel AI SDK Data Stream Protocol compatibility
- Message format conversion between AI SDK and Pydantic-AI
- Tool calling and streaming results back to frontend

Run with: fastapi run main.py or fastapi dev main.py
"""

# =============================================================================
# 1. IMPORTS & DEPENDENCIES
# =============================================================================

import json
import logging
from typing import Any, Dict, List, Optional

# Pydantic for data validation and models
from pydantic import BaseModel
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

# Pydantic-AI streaming events
from pydantic_ai.messages import (
    PartDeltaEvent,
    PartStartEvent,
)

logger = logging.getLogger(__name__)



# =============================================================================
# 3. PYDANTIC MODELS (Request/Response schemas)
# =============================================================================

class ChatMessageRequest(BaseModel):
    """
    Request model for agent chat messages.

    This matches the Vercel AI SDK message format:
    - messages: Array of conversation messages

    The 'messages' array contains objects with:
    - id: Unique message ID (optional)
    - role: 'user' or 'assistant'
    - content: Message text (fallback)
    - parts: Array of message parts (v5 format)
      - type: 'text' for text content, 'tool-call' for tool calls
      - text: The actual text content (for text parts)
    """
    messages: List[Dict[str, Any]]


# =============================================================================
# 3. VERCEL AI SDK COMPATIBILITY LAYER
# =============================================================================

def convert_vercel_messages_to_pydantic(
    messages: List[Dict[str, Any]],
    system_prompt_content: Optional[str] = None
) -> tuple[str, List[ModelMessage]]:
    """
    Convert Vercel AI SDK message format to Pydantic-AI format.

    The Vercel AI SDK uses a different message format than Pydantic-AI:

    Vercel AI SDK format:
    {
        "role": "user",
        "content": "What's 2 + 2?",
        "parts": [{"type": "text", "text": "What's 2 + 2?"}]
    }

    Pydantic-AI format:
    ModelRequest(parts=[UserPromptPart(content="What's 2 + 2?")])

    This function bridges that gap and handles:
    - Extracting the latest user message as the prompt
    - Converting previous messages to conversation history
    - Adding system prompt to the history
    - Handling tool calls and responses

    Args:
        messages: List of Vercel AI SDK message objects
        system_prompt_content: System prompt to include in history

    Returns:
        Tuple of (latest_user_message, message_history)
    """
    logger.info(f"Converting {len(messages) if messages else 0} messages")

    if not messages:
        return "", []

    # Extract the latest user message as the prompt
    latest_user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            parts = msg.get("parts", [])
            if parts:
                # v5 format: extract text from parts
                text_parts = [
                    p.get("text", "") for p in parts if p.get("type") == "text"
                ]
                latest_user_message = " ".join(text_parts)
            elif "content" in msg:
                # Fallback to direct content field
                latest_user_message = msg["content"]
            break

    # Convert all previous messages (excluding the latest) to ModelMessage format
    message_history = []

    # Always include system prompt at the beginning if provided
    if system_prompt_content:
        system_message = ModelRequest(
            parts=[SystemPromptPart(content=system_prompt_content)]
        )
        message_history.append(system_message)

    # Process all messages except the last one (which becomes the prompt)
    messages_except_last = messages[:-1] if messages else []

    for msg in messages_except_last:
        role = msg.get("role")

        if role == "user":
            # Convert user message to ModelRequest with UserPromptPart
            parts = msg.get("parts", [])
            text_content = ""
            if parts:
                text_parts = [
                    p.get("text", "") for p in parts if p.get("type") == "text"
                ]
                text_content = " ".join(text_parts)
            elif "content" in msg:
                text_content = msg["content"]

            user_message = ModelRequest(parts=[UserPromptPart(content=text_content)])
            message_history.append(user_message)

        elif role == "assistant":
            # Convert assistant message to ModelResponse
            parts = []
            msg_parts = msg.get("parts", [])

            # Handle text parts
            if msg_parts:
                text_parts = [
                    p.get("text", "") for p in msg_parts if p.get("type") == "text"
                ]
                if text_parts:
                    parts.append(TextPart(content=" ".join(text_parts)))
            elif "content" in msg:
                parts.append(TextPart(content=msg["content"]))

            # Handle tool calls (v5 format)
            tool_calls = []
            if msg_parts:
                for part in msg_parts:
                    if part.get("type") == "tool-call":
                        tool_calls.append(
                            ToolCallPart(
                                tool_name=part.get("toolName", ""),
                                args=part.get("input", {}),  # v5 uses 'input'
                                tool_call_id=part.get("toolCallId", ""),
                            )
                        )

            parts.extend(tool_calls)

            if parts:
                assistant_message = ModelResponse(parts=parts)
                message_history.append(assistant_message)

                # Add tool return messages for completed tool calls
                for tool_call in tool_calls:
                    # Look for tool results in the message parts
                    result = None
                    if msg_parts:
                        for part in msg_parts:
                            if (
                                part.get("type") == "tool-result"
                                and part.get("toolCallId") == tool_call.tool_call_id
                            ):
                                result = part.get("output")  # v5 uses 'output'
                                break

                    if result is not None:
                        tool_return = ModelRequest(
                            parts=[
                                ToolReturnPart(
                                    tool_name=tool_call.tool_name,
                                    content=result,
                                    tool_call_id=tool_call.tool_call_id,
                                )
                            ]
                        )
                        message_history.append(tool_return)

    return latest_user_message, message_history


async def to_data_stream_protocol(node, run):
    """Convert Pydantic AI agent stream node to Vercel AI SDK Data Stream Protocol.

    This implementation handles text streaming and tool calls for the math agent,
    emitting proper tool-input-available and tool-output-available events.

    Args:
        node: Agent stream node from agent.iter()
        run: Agent run context

    Yields:
        str: Data stream protocol formatted chunks
    """
    from pydantic_ai import Agent
    from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent

    if not hasattr(run, "_tool_calls_pending"):
        run._tool_calls_pending = {}
    if not hasattr(run, "_tool_name_map"):
        run._tool_name_map = {}

    if Agent.is_user_prompt_node(node):
        # User prompts are handled by the frontend, skip
        pass
    elif Agent.is_model_request_node(node):
        async with node.stream(run.ctx) as request_stream:
            async for event in request_stream:
                logger.info(f"📊 Event type: {type(event).__name__}")

                if isinstance(event, PartStartEvent):
                    if event.part.part_kind == "text":
                        if not hasattr(run, "_text_id"):
                            run._text_id = "text-" + str(id(event))
                        chunk = "data: {}\n\n".format(
                            json.dumps({"type": "text-start", "id": run._text_id})
                        )
                        yield chunk

                        # Check if PartStartEvent contains initial content
                        if hasattr(event.part, "content") and event.part.content:
                            initial_content = event.part.content
                            initial_chunk = "data: {}\n\n".format(
                                json.dumps({
                                    "type": "text-delta",
                                    "id": run._text_id,
                                    "delta": initial_content,
                                })
                            )
                            yield initial_chunk

                    elif event.part.part_kind == "tool-call":
                        run._tool_calls_pending[event.part.tool_call_id] = {
                            "toolName": event.part.tool_name,
                            "args_parts": [],
                        }

                elif isinstance(event, PartDeltaEvent):
                    if event.delta.part_delta_kind == "text":
                        if not hasattr(run, "_text_id"):
                            run._text_id = "text-main"
                        chunk = "data: {}\n\n".format(
                            json.dumps({
                                "type": "text-delta",
                                "id": run._text_id,
                                "delta": event.delta.content_delta,
                            })
                        )
                        yield chunk

    elif Agent.is_call_tools_node(node):
        # Handle tool calls with proper event emission
        async with node.stream(run.ctx) as tool_stream:
            async for event in tool_stream:
                if isinstance(event, FunctionToolCallEvent):
                    print(f"🔧 TOOL CALL STARTED: {event.part.tool_name}")
                    print(f"🔧 TOOL INPUT: {json.dumps(event.part.args, indent=2)}")

                    # Store tool name mapping
                    run._tool_name_map[event.part.tool_call_id] = event.part.tool_name

                    # Emit tool-input-available event
                    yield "data: {}\n\n".format(
                        json.dumps({
                            "type": "tool-input-available",
                            "toolCallId": event.part.tool_call_id,
                            "toolName": event.part.tool_name,
                            "input": event.part.args,
                        })
                    )

                elif isinstance(event, FunctionToolResultEvent):
                    print(f"🔧 TOOL RESULT RECEIVED for call_id: {event.result.tool_call_id}")
                    print(f"🔧 TOOL OUTPUT: {event.result.content}")

                    # Emit tool-output-available event
                    result_content = (
                        event.result.content.to_dict()
                        if hasattr(event.result.content, "to_dict")
                        else (
                            event.result.content.model_dump()
                            if hasattr(event.result.content, "model_dump")
                            else event.result.content
                        )
                    )

                    yield "data: {}\n\n".format(
                        json.dumps({
                            "type": "tool-output-available",
                            "toolCallId": event.result.tool_call_id,
                            "output": result_content,
                        })
                    )

    elif Agent.is_end_node(node):
        # Send text-end if we were streaming text
        if hasattr(run, "_text_id"):
            chunk = "data: {}\n\n".format(
                json.dumps({"type": "text-end", "id": run._text_id})
            )
            yield chunk
            delattr(run, "_text_id")


async def old_to_data_stream_protocol(agent_stream, run_context):
    """
    Convert Pydantic-AI agent stream to Vercel AI SDK Data Stream Protocol.

    The Vercel AI SDK expects Server-Sent Events (SSE) in a specific format:

    For text streaming:
    - data: {"type": "text-start", "id": "text-123"}
    - data: {"type": "text-delta", "id": "text-123", "delta": "Hello"}
    - data: {"type": "text-end", "id": "text-123"}

    For tool calls:
    - data: {"type": "tool-input-available", "toolCallId": "call-123", "toolName": "sum_numbers", "input": {...}}
    - data: {"type": "tool-output-available", "toolCallId": "call-123", "output": 42}

    This function converts Pydantic-AI's streaming events to this format.

    Args:
        agent_stream: The agent stream iterator from agent.run()
        run_context: Agent run context for tracking state

    Yields:
        str: SSE-formatted data chunks
    """
    # Track tool calls and text streaming
    if not hasattr(run_context, "_tool_calls_pending"):
        run_context._tool_calls_pending = {}

    text_id = None

    try:
        async for event in agent_stream:
            logger.info(f"Processing event: {type(event).__name__}")

            if isinstance(event, PartStartEvent):
                if event.part.part_kind == "text":
                    # Start streaming text
                    text_id = f"text-{id(event)}"
                    yield f"data: {json.dumps({'type': 'text-start', 'id': text_id})}\n\n"

                    # If there's initial content, send it
                    if hasattr(event.part, "content") and event.part.content:
                        yield f"data: {json.dumps({'type': 'text-delta', 'id': text_id, 'delta': event.part.content})}\n\n"

                elif event.part.part_kind == "tool-call":
                    # Track tool call start
                    tool_call_id = getattr(event.part, "tool_call_id", f"call-{id(event)}")
                    run_context._tool_calls_pending[tool_call_id] = {
                        "toolName": getattr(event.part, "tool_name", "unknown"),
                        "input_parts": []
                    }

            elif isinstance(event, PartDeltaEvent):
                if event.delta.part_delta_kind == "text" and text_id:
                    # Stream text delta
                    delta_content = getattr(event.delta, "content_delta", "")
                    yield f"data: {json.dumps({'type': 'text-delta', 'id': text_id, 'delta': delta_content})}\n\n"

                elif event.delta.part_delta_kind == "tool-call":
                    # Accumulate tool call arguments
                    tool_call_id = getattr(event.part, "tool_call_id", None)
                    if tool_call_id and tool_call_id in run_context._tool_calls_pending:
                        args_delta = getattr(event.delta, "args_delta", "")
                        run_context._tool_calls_pending[tool_call_id]["input_parts"].append(args_delta)

            # Handle completed tool calls and text endings
            # This is simplified - in the full version, you'd handle tool completion events

    except Exception as e:
        logger.error(f"Stream processing error: {e}")
        error_id = "error-text"
        yield f"data: {json.dumps({'type': 'text-start', 'id': error_id})}\n\n"
        yield f"data: {json.dumps({'type': 'text-delta', 'id': error_id, 'delta': f'Error: {str(e)}'})}\n\n"
        yield f"data: {json.dumps({'type': 'text-end', 'id': error_id})}\n\n"

    finally:
        # End text streaming if active
        if text_id:
            yield f"data: {json.dumps({'type': 'text-end', 'id': text_id})}\n\n"



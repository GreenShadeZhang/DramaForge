"""
DramaForge v2.0 — Chat API (Conversational Agent)
===================================================
Conversation CRUD + SSE streaming chat endpoint.
Adapted from IAA project patterns, using DramaForge's ai_hub.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.ai_hub import ChatMessage
from app.core.config import settings
from app.core.security import CurrentUser, DbSession
from app.engines.chat_engine import chat_engine
from app.models.media_generation import MediaGenerationJob, MediaJobStatus
from app.models.user import Conversation, Message, MessageRole
from app.core.billing_deps import require_credits, require_premium_model_access
from app.services.agent_intent import AgentIntent, AgentIntentResult, agent_intent_classifier
from app.services.media_generation_service import media_generation_service
from app.services.user_model_resolver import user_model_resolver
from app.tasks.media_generation_tasks import enqueue_media_job

router = APIRouter(prefix="/chat", tags=["Chat"])


# ═══════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════

class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    conversation_id: Optional[int] = Field(None, description="Existing conversation id (omit to create new)")
    mode: Optional[str] = Field(None, description="Agent mode: general / scriptwriter / director / project")
    project_id: Optional[int] = Field(None, description="Link chat to a project")
    stream: bool = Field(True, description="Whether to use SSE streaming")
    model: Optional[str] = Field(None, description="Override LLM model")
    model_capability: Optional[str] = Field(None, description="Selected model capability: chat / image / video")
    temperature: Optional[float] = Field(None, ge=0, le=2, description="Override temperature")


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    meta_json: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: int
    title: Optional[str] = None
    mode: Optional[str] = None
    project_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = []


class ChatCompletionResponse(BaseModel):
    message: MessageResponse
    conversation_id: int


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def sse_event(event: str, data: dict | str | None) -> str:
    """Format a Server-Sent Event string."""
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _build_history(messages: list[Message], limit: int = 20) -> list[ChatMessage]:
    """Convert DB messages to ChatMessage objects for the engine."""
    history: list[ChatMessage] = []
    for msg in messages[-limit:]:
        history.append(ChatMessage(role=msg.role.value, content=msg.content))
    return history


def _agent_media_routing_enabled(mode: str | None) -> bool:
    return (mode or "general") == "general"


def _classify_agent_intent(
    *,
    content: str,
    mode: str | None,
    model_capability: str | None = None,
) -> AgentIntentResult | None:
    if not _agent_media_routing_enabled(mode):
        return None

    capability = (model_capability or "").strip().lower()
    if capability in {"chat", "image", "video"}:
        detected = agent_intent_classifier.classify(content)
        return AgentIntentResult(
            intent=AgentIntent(capability),
            confidence=1.0,
            prompt=content.strip(),
            matched_by="selected_model",
            slots=detected.slots,
        )

    return agent_intent_classifier.classify(content)


def _media_request_json(intent: AgentIntentResult) -> dict:
    slots = dict(intent.slots or {})
    data: dict = {}

    if intent.intent == AgentIntent.IMAGE:
        if slots.get("image_size"):
            data["size"] = slots["image_size"]
        if slots.get("aspect_ratio"):
            data["aspect_ratio"] = slots["aspect_ratio"]
        return data

    if slots.get("duration"):
        data["duration"] = slots["duration"]
    if slots.get("video_resolution"):
        data["size"] = slots["video_resolution"]
        data["resolution"] = slots["video_resolution"]
    if slots.get("aspect_ratio"):
        data["aspect_ratio"] = slots["aspect_ratio"]
    return data


def _media_output_path(intent: AgentIntentResult) -> str:
    ext = "png" if intent.intent == AgentIntent.IMAGE else "mp4"
    return str(Path(settings.storage_dir) / "media_jobs" / f"job_pending.{ext}")


def _media_job_payload(job: MediaGenerationJob) -> dict:
    return {
        "id": job.id,
        "capability": job.capability.value,
        "provider_id": job.provider_id,
        "model_id": job.model_id,
        "provider_job_id": job.provider_job_id,
        "status": job.status.value,
        "progress": job.progress,
        "request_json": job.request_json or {},
        "result_assets_json": job.result_assets_json or [],
        "error": job.error,
    }


def _agent_media_response(intent: AgentIntentResult, job: MediaGenerationJob) -> str:
    label = "图片" if intent.intent == AgentIntent.IMAGE else "视频"
    status_text = "已提交" if job.status != MediaJobStatus.FAILED else "提交失败"

    if job.status == MediaJobStatus.FAILED:
        return (
            f"已识别为{label}生成需求，但任务提交失败。\n\n"
            f"- 任务 ID：{job.id}\n"
            f"- 模型：{job.model_id}\n"
            f"- 错误：{job.error or '未知错误'}"
        )

    return (
        f"已识别为{label}生成需求，并调用对应{label}模型创建生成任务。\n\n"
        f"- 任务 ID：{job.id}\n"
        f"- 状态：{status_text}\n"
        f"- 模型：{job.model_id}\n\n"
        "生成完成后，可在生成任务记录中查看结果。"
    )


async def _create_agent_media_job(
    *,
    db: DbSession,
    user_id: int,
    intent: AgentIntentResult,
    model_hint: str | None = None,
) -> MediaGenerationJob:
    job = await media_generation_service.create_job(
        db=db,
        user_id=user_id,
        capability=intent.intent.value,
        prompt=intent.prompt,
        output_path=_media_output_path(intent),
        model_hint=model_hint,
        request_json=_media_request_json(intent),
    )
    await db.commit()
    await db.refresh(job)

    try:
        queue_job_id = await enqueue_media_job(job.id)
    except Exception as exc:
        job.status = MediaJobStatus.FAILED
        job.error = f"Failed to enqueue media generation job: {exc}"[:2000]
        job.progress = 100
        await db.commit()
        await db.refresh(job)
        return job

    request_json = dict(job.request_json or {})
    request_json["_queue_job_id"] = queue_job_id
    job.request_json = request_json
    await db.commit()
    await db.refresh(job)
    return job


# ═══════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.post("/message")
async def send_message(
    request: SendMessageRequest,
    user: CurrentUser,
    db: DbSession,
):
    """
    Send a chat message.

    - If `stream=true` (default): returns SSE stream (`text/event-stream`)
    - If `stream=false`: returns JSON with full completion

    SSE events:
        - `conversation` — {id, title}
        - `user_message` — {id, content}
        - `delta`        — {content: "chunk..."}
        - `done`         — {message_id, finish_reason}
        - `error`        — {code, message}
    """

    conversation: Conversation | None = None
    if request.conversation_id:
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == request.conversation_id,
                Conversation.user_id == user.id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

    effective_mode = request.mode or (conversation.mode if conversation else None)
    agent_intent = _classify_agent_intent(
        content=request.content,
        mode=effective_mode,
        model_capability=request.model_capability,
    )

    if not (agent_intent and agent_intent.is_media):
        # ── Check premium model access for free users ─────────────
        if request.model:
            await require_premium_model_access(db, user.id, request.model)

        # ── Determine service type & consume credits ──────────────
        # Premium models: claude, gpt-4o, gpt-4.1 (non-mini)
        model_name = (request.model or "").lower()
        is_premium = any(k in model_name for k in ["claude", "gpt-4o", "gpt-4.1"]) and "mini" not in model_name
        credit_service = "chat_premium" if is_premium else "chat_default"

        await require_credits(
            db, user.id, credit_service,
            description=f"AI 对话 ({model_name or 'default'})",
        )

    if conversation is None:
        title = request.content[:50] + ("..." if len(request.content) > 50 else "")
        conversation = Conversation(
            user_id=user.id,
            title=title,
            mode=request.mode,
            project_id=request.project_id,
        )
        db.add(conversation)
        await db.flush()

    # ── Save user message ─────────────────────────────────────
    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=request.content,
    )
    db.add(user_message)
    await db.flush()

    # ── Build conversation history ────────────────────────────
    existing_messages = conversation.messages if request.conversation_id else []
    history = _build_history(existing_messages)

    mode = effective_mode

    resolved = None
    if not (agent_intent and agent_intent.is_media):
        resolved = await user_model_resolver.resolve(db, user.id, "chat", model_hint=request.model)

    # ══════════════════════════════════════════════════════════
    # Streaming mode (SSE)
    # ══════════════════════════════════════════════════════════
    if request.stream:
        async def event_generator():
            try:
                # Meta events
                yield sse_event("conversation", {
                    "id": conversation.id,
                    "title": conversation.title,
                })
                yield sse_event("user_message", {
                    "id": user_message.id,
                    "content": request.content,
                })

                if agent_intent and agent_intent.is_media:
                    yield sse_event("agent_intent", agent_intent.to_meta())
                    job = await _create_agent_media_job(
                        db=db,
                        user_id=user.id,
                        intent=agent_intent,
                        model_hint=request.model,
                    )
                    media_payload = _media_job_payload(job)
                    yield sse_event("media_job", media_payload)

                    full_content = _agent_media_response(agent_intent, job)
                    yield sse_event("delta", {"content": full_content})

                    assistant_message = Message(
                        conversation_id=conversation.id,
                        role=MessageRole.ASSISTANT,
                        content=full_content,
                        meta_json={
                            "agent_intent": agent_intent.to_meta(),
                            "media_job": media_payload,
                        },
                    )
                    db.add(assistant_message)
                    await db.commit()
                    await db.refresh(assistant_message)

                    yield sse_event("done", {
                        "message_id": assistant_message.id,
                        "finish_reason": "stop",
                        "agent_intent": agent_intent.intent.value,
                        "media_job_id": job.id,
                    })
                    return

                # Stream LLM response
                full_content = ""
                async for event in chat_engine.run_stream(
                    user_message=request.content,
                    mode=mode,
                    history=history,
                    model=resolved.model_id,
                    temperature=request.temperature,
                    api_key=resolved.api_key,
                    base_url=resolved.base_url,
                    chat_options=resolved.raw_params or {},
                ):
                    event_type = event["type"]
                    event_data = event["data"]

                    if event_type == "content":
                        full_content += event_data
                        yield sse_event("delta", {"content": event_data})
                    elif event_type == "error":
                        yield sse_event("error", {
                            "code": "STREAM_ERROR",
                            "message": event_data,
                        })
                        break
                    elif event_type == "done":
                        break

                # Save assistant message to DB
                assistant_message = Message(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT,
                    content=full_content,
                )
                db.add(assistant_message)
                await db.commit()
                await db.refresh(assistant_message)

                yield sse_event("done", {
                    "message_id": assistant_message.id,
                    "finish_reason": "stop",
                })

            except Exception as exc:
                yield sse_event("error", {
                    "code": "STREAM_ERROR",
                    "message": str(exc),
                })

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # ══════════════════════════════════════════════════════════
    # Non-streaming mode
    # ══════════════════════════════════════════════════════════
    if agent_intent and agent_intent.is_media:
        job = await _create_agent_media_job(
            db=db,
            user_id=user.id,
            intent=agent_intent,
            model_hint=request.model,
        )
        media_payload = _media_job_payload(job)
        content = _agent_media_response(agent_intent, job)
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=content,
            meta_json={
                "agent_intent": agent_intent.to_meta(),
                "media_job": media_payload,
            },
        )
        db.add(assistant_message)
        await db.commit()
        await db.refresh(assistant_message)

        return ChatCompletionResponse(
            conversation_id=conversation.id,
            message=MessageResponse(
                id=assistant_message.id,
                conversation_id=conversation.id,
                role=assistant_message.role.value,
                content=assistant_message.content,
                meta_json=assistant_message.meta_json,
                created_at=assistant_message.created_at,
            ),
        )

    content = await chat_engine.run(
        user_message=request.content,
        mode=mode,
        history=history,
        model=resolved.model_id,
        temperature=request.temperature,
        api_key=resolved.api_key,
        base_url=resolved.base_url,
        chat_options=resolved.raw_params or {},
    )

    assistant_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=content,
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)

    return ChatCompletionResponse(
        conversation_id=conversation.id,
        message=MessageResponse(
            id=assistant_message.id,
            conversation_id=conversation.id,
            role=assistant_message.role.value,
            content=assistant_message.content,
            meta_json=assistant_message.meta_json,
            created_at=assistant_message.created_at,
        ),
    )


# ═══════════════════════════════════════════════════════════════════
# Conversation CRUD
# ═══════════════════════════════════════════════════════════════════

@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List user conversations, newest first."""
    count_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == user.id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    conversations = result.scalars().all()

    items = []
    for conv in conversations:
        msg_count_result = await db.execute(
            select(func.count(Message.id)).where(Message.conversation_id == conv.id)
        )
        msg_count = msg_count_result.scalar() or 0
        items.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            mode=conv.mode,
            project_id=conv.project_id,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=msg_count,
        ))

    return items


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    user: CurrentUser,
    db: DbSession,
):
    """Get a conversation with all messages."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        mode=conversation.mode,
        project_id=conversation.project_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(conversation.messages),
        messages=[
            MessageResponse(
                id=msg.id,
                conversation_id=conversation.id,
                role=msg.role.value,
                content=msg.content,
                meta_json=msg.meta_json,
                created_at=msg.created_at,
            )
            for msg in conversation.messages
        ],
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    user: CurrentUser,
    db: DbSession,
):
    """Delete a conversation and all its messages."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    await db.delete(conversation)
    await db.commit()

    return {"deleted": True, "conversation_id": conversation_id}

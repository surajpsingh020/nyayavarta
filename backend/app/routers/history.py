"""Chat History Router (/api/chat/threads) for Nyayavarta.

Provides endpoints to manage consultation threads and messages, strictly
isolated per authenticated user. Users can NEVER access other users' threads.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status

from app.models.schemas import (
    CreateThreadRequest,
    ThreadResponse,
    ThreadMessageItem,
)
from app.routers.auth import get_current_authenticated_user
from app.services.auth_db import get_auth_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/chat/threads", response_model=List[ThreadResponse], summary="List consultation threads for authenticated user")
async def list_threads(user: dict = Depends(get_current_authenticated_user)):
    """Return all consultation threads belonging strictly to the authenticated user."""
    auth_db = get_auth_db()
    threads = auth_db.get_user_threads(user["id"])
    return [ThreadResponse(**t) for t in threads]


@router.post("/chat/threads", response_model=ThreadResponse, summary="Create a new consultation thread")
async def create_thread(
    payload: CreateThreadRequest,
    user: dict = Depends(get_current_authenticated_user)
):
    """Create a new consultation thread for the authenticated user."""
    auth_db = get_auth_db()
    thread = auth_db.create_thread(
        user_id=user["id"],
        title=payload.title
    )
    return ThreadResponse(**thread)


@router.get("/chat/threads/{thread_id}/messages", response_model=List[ThreadMessageItem], summary="Get messages in a consultation thread")
async def get_thread_messages(
    thread_id: str,
    user: dict = Depends(get_current_authenticated_user)
):
    """Retrieve messages for a thread owned by the authenticated user."""
    auth_db = get_auth_db()
    # Strict isolation check: verify thread ownership
    thread = auth_db.get_thread(user["id"], thread_id)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation thread not found or access denied."
        )

    messages = auth_db.get_thread_messages(user["id"], thread_id)
    return [ThreadMessageItem(**m) for m in messages]


@router.delete("/chat/threads/{thread_id}", summary="Delete a consultation thread")
async def delete_thread(
    thread_id: str,
    user: dict = Depends(get_current_authenticated_user)
):
    """Delete a thread and its messages if owned by the authenticated user."""
    auth_db = get_auth_db()
    deleted = auth_db.delete_thread(user["id"], thread_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation thread not found or access denied."
        )
    return {"status": "success", "message": "Thread deleted successfully."}

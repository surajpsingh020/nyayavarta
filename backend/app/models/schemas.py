from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class UserProfile(str, Enum):
    STUDENT = "student"
    PROFESSIONAL = "professional"
    SENIOR_CITIZEN = "senior_citizen"
    GENERAL = "general"


class ChatRequest(BaseModel):
    """Request schema for the /chat endpoint."""
    text: Optional[str] = Field(None, description="User's text input")
    audio_base64: Optional[str] = Field(None, description="Base64-encoded audio input")
    source_language: str = Field("hi", description="BCP-47 language code (e.g., 'hi', 'ta', 'bn')")
    user_profile: UserProfile = Field(UserProfile.GENERAL, description="User's profile category")


class ChatResponse(BaseModel):
    """Response schema for the /chat endpoint."""
    original_query: str = Field(..., description="User's original input")
    english_query: str = Field(..., description="English translation of input")
    regional_response: str = Field(..., description="Response in user's language")
    english_response: str = Field(..., description="Response in English")
    citations: list[dict] = Field(default_factory=list, description="Legal citations")
    audio_base64: Optional[str] = Field(None, description="Base64-encoded TTS audio")


class UploadResponse(BaseModel):
    """Response schema for the /upload endpoint."""
    filename: str
    chunks_created: int
    message: str


class HealthResponse(BaseModel):
    status: str
    service: str

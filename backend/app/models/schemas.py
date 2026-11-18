from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
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
    thread_id: Optional[str] = Field(None, description="Active consultation thread ID")
    document_name: Optional[str] = Field(None, description="Filename of currently active/attached user document")


class ChatResponse(BaseModel):
    """Response schema for the /chat endpoint."""
    original_query: str = Field(..., description="User's original input")
    english_query: str = Field(..., description="English translation of input")
    regional_response: str = Field(..., description="Response in user's language")
    english_response: str = Field(..., description="Response in English")
    citations: list[dict] = Field(default_factory=list, description="Legal citations")
    audio_base64: Optional[str] = Field(None, description="Base64-encoded TTS audio")
    detected_language: Optional[str] = Field("hi", description="Detected language code (e.g. 'bn', 'hi', 'en')")
    thread_id: Optional[str] = Field(None, description="Associated consultation thread ID")


class TranslateRequest(BaseModel):
    """Request schema for on-demand response translation."""
    text: str = Field(..., description="Text to translate")
    target_language: str = Field(..., description="Target BCP-47 language code")
    source_language: Optional[str] = Field("en", description="Source language code")


class TranslateResponse(BaseModel):
    """Response schema for on-demand response translation."""
    translated_text: str = Field(..., description="Translated text")
    target_language: str = Field(..., description="Target language code")
    audio_base64: Optional[str] = Field(None, description="Base64-encoded TTS audio for translated text")


class UploadResponse(BaseModel):
    """Response schema for the /upload endpoint."""
    filename: str
    chunks_created: int
    message: str


class HealthResponse(BaseModel):
    status: str
    service: str


# -----------------------------------------------------------------
# Authentication & User Management Schemas
# -----------------------------------------------------------------
class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (at least 6 characters)")
    full_name: str = Field(..., min_length=1, description="Full name of the user")


class UserLoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Password")


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


# -----------------------------------------------------------------
# Chat History & Consultation Thread Schemas
# -----------------------------------------------------------------
class CreateThreadRequest(BaseModel):
    title: Optional[str] = Field(None, description="Optional custom title for the consultation")


class ThreadResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class ThreadMessageItem(BaseModel):
    id: str
    thread_id: str
    sender: str
    original_query: Optional[str] = None
    english_query: Optional[str] = None
    regional_response: Optional[str] = None
    english_response: Optional[str] = None
    citations: list[dict] = Field(default_factory=list)
    audio_base64: Optional[str] = None
    detected_language: Optional[str] = "hi"
    created_at: str

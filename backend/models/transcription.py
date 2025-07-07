from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class TranscriptionRequest(BaseModel):
    """Model for transcription request"""
    source_language: str = Field(default="hi", description="Source language code")
    target_language: str = Field(default="en", description="Target language code")
    model_name: str = Field(default="bhashini", description="AI model to use")

class TranscriptionResponse(BaseModel):
    """Model for transcription response"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transcript: str = Field(description="Original transcript")
    translation: str = Field(description="Translated text")
    translated_audio: str = Field(description="Base64 encoded translated audio")
    source_language: str = Field(description="Source language code")
    target_language: str = Field(description="Target language code")
    model_name: str = Field(description="AI model used")
    processing_time: float = Field(description="Processing time in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TranscriptionRecord(BaseModel):
    """Database model for transcription record"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str = Field(description="Original filename")
    file_size: int = Field(description="File size in bytes")
    transcript: str = Field(description="Original transcript")
    translation: str = Field(description="Translated text")
    translated_audio: str = Field(description="Base64 encoded translated audio")
    source_language: str = Field(description="Source language code")
    target_language: str = Field(description="Target language code")
    model_name: str = Field(description="AI model used")
    processing_time: float = Field(description="Processing time in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = Field(None, description="User ID if authenticated")

class AudioUploadResponse(BaseModel):
    """Response model for audio upload"""
    message: str = Field(description="Status message")
    file_id: str = Field(description="Unique file identifier")
    filename: str = Field(description="Original filename")
    file_size: int = Field(description="File size in bytes")
    supported_formats: list = Field(description="List of supported audio formats")

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")
    code: Optional[str] = Field(None, description="Error code")

class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str = Field(description="Service status")
    version: str = Field(description="API version")
    services: Dict[str, str] = Field(description="Service statuses")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SupportedLanguagesResponse(BaseModel):
    """Response model for supported languages"""
    source_languages: Dict[str, str] = Field(description="Supported source languages")
    target_languages: Dict[str, str] = Field(description="Supported target languages")
    models: Dict[str, str] = Field(description="Available AI models")
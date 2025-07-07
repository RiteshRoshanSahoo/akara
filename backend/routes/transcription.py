import os
import tempfile
import time
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
import logging
from pathlib import Path

# Import models and services
from models.transcription import (
    TranscriptionRequest, TranscriptionResponse, TranscriptionRecord,
    AudioUploadResponse, ErrorResponse, SupportedLanguagesResponse
)
from services.bhashini_agent import BhashiniAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/transcription", tags=["transcription"])

# Initialize Bhashini agent
try:
    bhashini_agent = BhashiniAgent()
    logger.info("BhashiniAgent initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize BhashiniAgent: {e}")
    bhashini_agent = None

# Database connection (will be injected)
db = None

def get_database():
    """Get database connection"""
    global db
    if db is None:
        from server import db as server_db
        db = server_db
    return db

# Supported audio formats
SUPPORTED_FORMATS = [
    "audio/wav", "audio/wave", "audio/x-wav",
    "audio/mpeg", "audio/mp3", "audio/x-mp3",
    "audio/mp4", "audio/x-mp4", "audio/aac",
    "audio/ogg", "audio/flac", "audio/x-flac"
]

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

@router.post("/upload", response_model=AudioUploadResponse)
async def upload_audio_file(
    file: UploadFile = File(...),
    source_language: str = Form(default="hi"),
    target_language: str = Form(default="en"),
    model_name: str = Form(default="bhashini")
):
    """
    Upload audio file for transcription and translation
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        if file.content_type not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
            )
        
        # Check file size
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE/1024/1024:.1f}MB"
            )
        
        # Reset file position
        await file.seek(0)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            tmp_file.write(contents)
            temp_file_path = tmp_file.name
        
        logger.info(f"Audio file uploaded: {file.filename} ({len(contents)} bytes)")
        
        # Process transcription in background
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            process_transcription,
            temp_file_path,
            file.filename,
            len(contents),
            source_language,
            target_language,
            model_name
        )
        
        return AudioUploadResponse(
            message="File uploaded successfully. Processing started.",
            file_id=Path(temp_file_path).stem,
            filename=file.filename,
            file_size=len(contents),
            supported_formats=SUPPORTED_FORMATS
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during file upload")

async def process_transcription(
    file_path: str,
    filename: str,
    file_size: int,
    source_language: str,
    target_language: str,
    model_name: str
):
    """
    Background task to process transcription
    """
    try:
        if bhashini_agent is None:
            logger.error("BhashiniAgent not initialized")
            return
        
        start_time = time.time()
        
        # Run transcription pipeline
        result = bhashini_agent.run_pipeline(
            file_path, 
            source_language, 
            target_language
        )
        
        processing_time = time.time() - start_time
        
        # Create record for database
        record = TranscriptionRecord(
            filename=filename,
            file_size=file_size,
            transcript=result["transcript"],
            translation=result["translation"],
            translated_audio=result["translated_audio"],
            source_language=source_language,
            target_language=target_language,
            model_name=model_name,
            processing_time=processing_time
        )
        
        # Save to database
        db = get_database()
        await db.transcriptions.insert_one(record.dict())
        
        logger.info(f"Transcription completed for {filename} in {processing_time:.2f}s")
        
    except Exception as e:
        logger.error(f"Error processing transcription: {e}")
    finally:
        # Clean up temporary file
        try:
            os.unlink(file_path)
        except:
            pass

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    source_language: str = Form(default="hi"),
    target_language: str = Form(default="en"),
    model_name: str = Form(default="bhashini")
):
    """
    Transcribe and translate audio file synchronously
    """
    try:
        if bhashini_agent is None:
            raise HTTPException(status_code=503, detail="Transcription service not available")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        if file.content_type not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
            )
        
        # Check file size
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE/1024/1024:.1f}MB"
            )
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            tmp_file.write(contents)
            temp_file_path = tmp_file.name
        
        try:
            start_time = time.time()
            
            # Run transcription pipeline
            result = bhashini_agent.run_pipeline(
                temp_file_path,
                source_language,
                target_language
            )
            
            processing_time = time.time() - start_time
            
            # Create response
            response = TranscriptionResponse(
                transcript=result["transcript"],
                translation=result["translation"],
                translated_audio=result["translated_audio"],
                source_language=source_language,
                target_language=target_language,
                model_name=model_name,
                processing_time=processing_time
            )
            
            # Save to database
            record = TranscriptionRecord(
                filename=file.filename,
                file_size=len(contents),
                transcript=result["transcript"],
                translation=result["translation"],
                translated_audio=result["translated_audio"],
                source_language=source_language,
                target_language=target_language,
                model_name=model_name,
                processing_time=processing_time
            )
            
            db = get_database()
            await db.transcriptions.insert_one(record.dict())
            
            logger.info(f"Transcription completed for {file.filename} in {processing_time:.2f}s")
            
            return response
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during transcription")

@router.get("/languages", response_model=SupportedLanguagesResponse)
async def get_supported_languages():
    """
    Get supported languages and models
    """
    try:
        if bhashini_agent is None:
            raise HTTPException(status_code=503, detail="Transcription service not available")
        
        languages = bhashini_agent.get_supported_languages()
        
        return SupportedLanguagesResponse(
            source_languages=languages["source_languages"],
            target_languages=languages["target_languages"],
            models={"bhashini": "Bhashini (Government of India)"}
        )
        
    except Exception as e:
        logger.error(f"Error getting supported languages: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/history")
async def get_transcription_history(limit: int = 10, offset: int = 0):
    """
    Get transcription history
    """
    try:
        db = get_database()
        
        # Get total count
        total = await db.transcriptions.count_documents({})
        
        # Get records
        cursor = db.transcriptions.find({}).sort("created_at", -1).skip(offset).limit(limit)
        records = await cursor.to_list(length=limit)
        
        # Convert to response format
        history = []
        for record in records:
            history.append({
                "id": record["id"],
                "filename": record["filename"],
                "transcript": record["transcript"][:100] + "..." if len(record["transcript"]) > 100 else record["transcript"],
                "translation": record["translation"][:100] + "..." if len(record["translation"]) > 100 else record["translation"],
                "source_language": record["source_language"],
                "target_language": record["target_language"],
                "model_name": record["model_name"],
                "processing_time": record["processing_time"],
                "created_at": record["created_at"]
            })
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "history": history
        }
        
    except Exception as e:
        logger.error(f"Error getting transcription history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    try:
        services = {
            "bhashini_agent": "healthy" if bhashini_agent is not None else "unhealthy",
            "database": "healthy"
        }
        
        # Test database connection
        try:
            db = get_database()
            await db.transcriptions.count_documents({})
        except:
            services["database"] = "unhealthy"
        
        return {
            "status": "healthy" if all(s == "healthy" for s in services.values()) else "degraded",
            "version": "1.0.0",
            "services": services,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )
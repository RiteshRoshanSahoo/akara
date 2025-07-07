import os
import sys
from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
import uuid
from datetime import datetime

# Add backend directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import transcription routes
try:
    from routes.transcription import router as transcription_router
except ImportError:
    # Fallback import for development
    sys.path.append('/app/backend')
    from routes.transcription import router as transcription_router

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(
    title="Akara - Multilingual AI-Based Voice Meeting System",
    description="Team MOM Hackathon presents Akara - Advanced audio transcription and translation system",
    version="1.0.0"
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {
        "message": "Akara Backend API is running",
        "version": "1.0.0",
        "description": "Multilingual AI-Based Voice Meeting System",
        "team": "Team MOM Hackathon"
    }

@api_router.get("/health")
async def health_check():
    """Comprehensive health check"""
    try:
        # Test database connection
        await db.status_checks.count_documents({})
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"
    
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "version": "1.0.0",
        "service": "Akara API",
        "timestamp": datetime.utcnow().isoformat()
    }

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the main API router
app.include_router(api_router)

# Include transcription routes
app.include_router(transcription_router)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Akara API server...")
    logger.info("Team MOM Hackathon - Akara v1.0.0")
    
    # Test database connection
    try:
        await db.status_checks.count_documents({})
        logger.info("Database connection established successfully")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
    
    # Initialize transcription service
    try:
        from services.bhashini_agent import BhashiniAgent
        agent = BhashiniAgent()
        logger.info("BhashiniAgent initialized successfully")
    except Exception as e:
        logger.error(f"BhashiniAgent initialization failed: {e}")
        logger.error("Make sure to set your API keys in the .env file")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Clean up on shutdown"""
    logger.info("Shutting down Akara API server...")
    client.close()

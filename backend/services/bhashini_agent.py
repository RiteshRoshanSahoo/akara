import os
import io
import base64
import json
import time
import requests
import logging
from typing import Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from langdetect import detect
from pydub import AudioSegment
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BhashiniAgent:
    def __init__(self):
        self.setup_credentials()
        self.pipeline_id = "64392f96daac500b55c543cd"  # MeitY pipeline
        self.config_url = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
        self.pipeline_cache = {}

    def setup_credentials(self):
        """Setup API credentials from environment variables"""
        self.user_id = os.getenv("BHASHINI_USER_ID")
        self.ulca_api_key = os.getenv("ULCA_API_KEY")
        self.auth_token = os.getenv("BHASHINI_AUTH_TOKEN")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        
        # Check if credentials are still placeholders
        if (self.user_id == "your_user_id_here" or 
            self.ulca_api_key == "your_ulca_key_here" or 
            self.auth_token == "your_auth_token_here" or
            not self.user_id or not self.ulca_api_key or not self.auth_token):
            raise ValueError("Bhashini API credentials not configured. Please update .env file with real API keys.")
        
        logger.info("BhashiniAgent credentials loaded successfully")

    def get_pipeline_config(self, task_list):
        """Get pipeline configuration from Bhashini API"""
        headers = {
            "userID": self.user_id,
            "ulcaApiKey": self.ulca_api_key,
            "Authorization": self.auth_token,
            "Content-Type": "application/json"
        }
        
        payload = {
            "pipelineTasks": task_list,
            "pipelineRequestConfig": {"pipelineId": self.pipeline_id}
        }
        
        response = requests.post(self.config_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def encode_audio(self, audio_path):
        """Encode audio file to base64 with proper formatting"""
        audio = AudioSegment.from_file(audio_path)
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        buf = io.BytesIO()
        audio.export(buf, format="wav")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def run_pipeline(self, audio_path, source_lang="hi", target_lang="en"):
        """
        Run complete pipeline: ASR -> Translation -> TTS
        Returns: {
            "transcript": "original transcript",
            "translation": "translated text", 
            "translated_audio": "base64 encoded audio"
        }
        """
        audio_base64 = self.encode_audio(audio_path)

        tasks = [
            {"taskType": "asr", "config": {"language": {"sourceLanguage": source_lang}}},
            {"taskType": "translation", "config": {"language": {"sourceLanguage": source_lang, "targetLanguage": target_lang}}},
            {"taskType": "tts", "config": {"language": {"sourceLanguage": target_lang}}}
        ]

        config = self.get_pipeline_config(tasks)
        callback_url = config["pipelineInferenceAPIEndPoint"]["callbackUrl"]
        auth_name = config["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["name"]
        auth_value = config["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["value"]

        headers = {
            auth_name: auth_value,
            "Content-Type": "application/json"
        }

        compute_payload = {
            "pipelineTasks": [
                {
                    "taskType": "asr",
                    "config": {
                        "language": {"sourceLanguage": source_lang},
                        "serviceId": config["pipelineResponseConfig"][0]["config"][0]["serviceId"],
                        "audioFormat": "wav",
                        "samplingRate": 16000
                    }
                },
                {
                    "taskType": "translation",
                    "config": {
                        "language": {"sourceLanguage": source_lang, "targetLanguage": target_lang},
                        "serviceId": config["pipelineResponseConfig"][1]["config"][0]["serviceId"]
                    }
                },
                {
                    "taskType": "tts",
                    "config": {
                        "language": {"sourceLanguage": target_lang},
                        "serviceId": config["pipelineResponseConfig"][2]["config"][0]["serviceId"],
                        "gender": "female",
                        "audioFormat": "wav",
                        "samplingRate": 22050
                    }
                }
            ],
            "inputData": {
                "audio": [{"audioContent": audio_base64}],
                "input": [{"source": ""}]
            }
        }

        response = requests.post(callback_url, json=compute_payload, headers=headers)
        response.raise_for_status()
        output = response.json()
        logger.info(json.dumps(output, indent=2))

        # Extract results according to your original code structure
        transcript = output["pipelineResponse"][0]["output"][0]["source"]
        translation = output["pipelineResponse"][1]["output"][0]["target"]
        translated_audio = output["pipelineResponse"][2]["audio"][0]["audioContent"]
        
        return {
            "transcript": transcript,
            "translation": translation,
            "translated_audio": translated_audio,
            "source_language": source_lang,
            "target_language": target_lang,
            "processing_time": time.time()
        }

    def get_supported_languages(self) -> Dict:
        """Get list of supported languages"""
        return {
            "source_languages": {
                "hi": "Hindi",
                "en": "English", 
                "bn": "Bengali",
                "gu": "Gujarati",
                "kn": "Kannada",
                "ml": "Malayalam",
                "mr": "Marathi",
                "or": "Odia",
                "pa": "Punjabi",
                "ta": "Tamil",
                "te": "Telugu",
                "ur": "Urdu"
            },
            "target_languages": {
                "en": "English",
                "hi": "Hindi",
                "bn": "Bengali",
                "gu": "Gujarati",
                "kn": "Kannada",
                "ml": "Malayalam",
                "mr": "Marathi",
                "or": "Odia",
                "pa": "Punjabi",
                "ta": "Tamil",
                "te": "Telugu",
                "ur": "Urdu"
            }
        }
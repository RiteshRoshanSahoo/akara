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
        
        # Validate required credentials
        if not all([self.user_id, self.ulca_api_key, self.auth_token]):
            raise ValueError("Missing required Bhashini API credentials. Please check your .env file.")
        
        logger.info("BhashiniAgent credentials loaded successfully")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
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
        
        try:
            response = requests.post(self.config_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            logger.info("Pipeline configuration retrieved successfully")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting pipeline config: {e}")
            raise

    def encode_audio(self, audio_path: str) -> str:
        """Encode audio file to base64 with proper formatting"""
        try:
            # Load and process audio
            audio = AudioSegment.from_file(audio_path)
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            
            # Convert to base64
            buf = io.BytesIO()
            audio.export(buf, format="wav")
            encoded_audio = base64.b64encode(buf.getvalue()).decode("utf-8")
            
            logger.info(f"Audio encoded successfully. Duration: {len(audio)/1000:.2f}s")
            return encoded_audio
        
        except Exception as e:
            logger.error(f"Error encoding audio: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def run_pipeline(self, audio_path: str, source_lang: str = "hi", target_lang: str = "en") -> Dict:
        """
        Run complete pipeline: ASR -> Translation -> TTS
        Returns: {
            "transcript": "original transcript",
            "translation": "translated text", 
            "translated_audio": "base64 encoded audio"
        }
        """
        try:
            logger.info(f"Starting pipeline processing: {source_lang} -> {target_lang}")
            
            # Encode audio
            audio_base64 = self.encode_audio(audio_path)
            
            # Define pipeline tasks
            tasks = [
                {"taskType": "asr", "config": {"language": {"sourceLanguage": source_lang}}},
                {"taskType": "translation", "config": {"language": {"sourceLanguage": source_lang, "targetLanguage": target_lang}}},
                {"taskType": "tts", "config": {"language": {"sourceLanguage": target_lang}}}
            ]
            
            # Get pipeline configuration
            config = self.get_pipeline_config(tasks)
            
            # Extract callback URL and auth details
            callback_url = config["pipelineInferenceAPIEndPoint"]["callbackUrl"]
            auth_name = config["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["name"]
            auth_value = config["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["value"]
            
            # Prepare headers
            headers = {
                auth_name: auth_value,
                "Content-Type": "application/json"
            }
            
            # Prepare compute payload
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
            
            # Make the request
            response = requests.post(callback_url, json=compute_payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            # Process response
            output = response.json()
            logger.info("Pipeline processing completed successfully")
            
            # Extract results
            transcript = output["pipelineResponse"][0]["output"][0]["source"]
            translation = output["pipelineResponse"][1]["output"][0]["target"]
            translated_audio = output["pipelineResponse"][2]["audio"][0]["audioContent"]
            
            result = {
                "transcript": transcript,
                "translation": translation,
                "translated_audio": translated_audio,
                "source_language": source_lang,
                "target_language": target_lang,
                "processing_time": time.time()
            }
            
            logger.info(f"Pipeline results: transcript={len(transcript)} chars, translation={len(translation)} chars")
            return result
            
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            raise

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

    def detect_language(self, text: str) -> str:
        """Detect language of input text"""
        try:
            detected = detect(text)
            # Map detected languages to supported ones
            lang_mapping = {
                'hi': 'hi', 'en': 'en', 'bn': 'bn', 'gu': 'gu',
                'kn': 'kn', 'ml': 'ml', 'mr': 'mr', 'or': 'or',
                'pa': 'pa', 'ta': 'ta', 'te': 'te', 'ur': 'ur'
            }
            return lang_mapping.get(detected, 'hi')  # Default to Hindi
        except:
            return 'hi'  # Default fallback
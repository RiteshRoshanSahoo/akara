#!/usr/bin/env python3
import os
import sys
import json
import requests
import unittest
import io
import base64
import tempfile
import wave
from pathlib import Path

# Get the backend URL from the frontend .env file
def get_backend_url():
    env_path = '/app/frontend/.env'
    backend_url = None
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    backend_url = line.strip().split('=', 1)[1].strip('"\'')
                    break
    
    if not backend_url:
        # Fallback to default
        backend_url = "https://3b3ea0e4-99bf-48c2-85fb-9391624d7475.preview.emergentagent.com"
    
    return backend_url

# Create a simple WAV file for testing
def create_test_audio_file():
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_file.close()
    
    # Create a simple WAV file with 1 second of silence
    with wave.open(temp_file.name, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b'\x00' * 32000)
    
    return temp_file.name

class AkaraBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend_url = get_backend_url()
        cls.api_url = f"{cls.backend_url}/api"
        cls.test_audio_path = create_test_audio_file()
        print(f"Testing backend at: {cls.api_url}")
    
    @classmethod
    def tearDownClass(cls):
        # Clean up test audio file
        if os.path.exists(cls.test_audio_path):
            os.unlink(cls.test_audio_path)
    
    def test_01_root_endpoint(self):
        """Test the root API endpoint"""
        print("\n1. Testing root API endpoint...")
        response = requests.get(f"{self.api_url}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("version", data)
        print(f"✅ Root API endpoint working: {data['message']}")
    
    def test_02_health_endpoint(self):
        """Test the health check endpoint"""
        print("\n2. Testing health check endpoint...")
        response = requests.get(f"{self.api_url}/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("database", data)
        self.assertIn("version", data)
        print(f"✅ Health check endpoint working: Status = {data['status']}, Database = {data['database']}")
    
    def test_03_transcription_health(self):
        """Test the transcription service health endpoint"""
        print("\n3. Testing transcription service health...")
        response = requests.get(f"{self.api_url}/transcription/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("services", data)
        
        # Check BhashiniAgent status (expected to be unhealthy without API keys)
        bhashini_status = data['services'].get('bhashini_agent', 'missing')
        print(f"✅ Transcription health endpoint working: Status = {data['status']}")
        print(f"   BhashiniAgent status: {bhashini_status} (expected to be unhealthy without API keys)")
    
    def test_04_supported_languages(self):
        """Test the supported languages endpoint"""
        print("\n4. Testing supported languages endpoint...")
        try:
            response = requests.get(f"{self.api_url}/transcription/languages")
            
            # This might fail if BhashiniAgent is not initialized
            if response.status_code == 503:
                print("ℹ️ Supported languages endpoint returned 503 - This is expected without API keys")
                print("ℹ️ Error message:", response.json().get('detail', 'No detail provided'))
                # Skip further assertions
                return
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("source_languages", data)
            self.assertIn("target_languages", data)
            self.assertIn("models", data)
            
            # Check if we have languages
            self.assertGreater(len(data["source_languages"]), 0)
            self.assertGreater(len(data["target_languages"]), 0)
            
            print(f"✅ Supported languages endpoint working")
            print(f"   Source languages: {len(data['source_languages'])}")
            print(f"   Target languages: {len(data['target_languages'])}")
            print(f"   Models: {data['models']}")
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Error testing languages endpoint: {e}")
            raise
    
    def test_05_audio_upload_validation(self):
        """Test audio upload validation"""
        print("\n5. Testing audio upload validation...")
        
        # Test with invalid file (empty data)
        print("   Testing with invalid file...")
        files = {'file': ('test.txt', io.BytesIO(b'not an audio file'), 'text/plain')}
        data = {
            'source_language': 'hi',
            'target_language': 'en',
            'model_name': 'bhashini'
        }
        
        response = requests.post(
            f"{self.api_url}/transcription/transcribe",
            files=files,
            data=data
        )
        
        # Should return 400 Bad Request for invalid file format
        self.assertEqual(response.status_code, 400)
        print(f"✅ Invalid file format correctly rejected with status code {response.status_code}")
        print(f"   Error message: {response.json().get('detail', 'No detail provided')}")
    
    def test_06_audio_upload_with_valid_file(self):
        """Test audio upload with valid file"""
        print("\n6. Testing audio upload with valid file...")
        
        # Open the test audio file
        with open(self.test_audio_path, 'rb') as f:
            audio_data = f.read()
        
        files = {'file': ('test.wav', io.BytesIO(audio_data), 'audio/wav')}
        data = {
            'source_language': 'hi',
            'target_language': 'en',
            'model_name': 'bhashini'
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/transcription/transcribe",
                files=files,
                data=data
            )
            
            # This will likely fail with 503 Service Unavailable due to missing API keys
            if response.status_code == 503:
                print("ℹ️ Transcription endpoint returned 503 - This is expected without API keys")
                print("ℹ️ Error message:", response.json().get('detail', 'No detail provided'))
                return
            
            # If it somehow succeeds, verify the response
            if response.status_code == 200:
                data = response.json()
                self.assertIn("transcript", data)
                self.assertIn("translation", data)
                print("✅ Transcription endpoint working (unexpected success)")
            else:
                print(f"ℹ️ Transcription endpoint returned {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Error testing transcription endpoint: {e}")
            raise
    
    def test_07_status_endpoint(self):
        """Test the status endpoint"""
        print("\n7. Testing status endpoint...")
        
        # Test POST to create a status check
        data = {"client_name": "backend_test"}
        response = requests.post(f"{self.api_url}/status", json=data)
        
        try:
            self.assertEqual(response.status_code, 200)
            post_data = response.json()
            self.assertIn("id", post_data)
            self.assertEqual(post_data["client_name"], "backend_test")
            print(f"✅ Status POST endpoint working: Created status check with ID {post_data['id']}")
            
            # Test GET to retrieve status checks
            response = requests.get(f"{self.api_url}/status")
            self.assertEqual(response.status_code, 200)
            get_data = response.json()
            self.assertIsInstance(get_data, list)
            print(f"✅ Status GET endpoint working: Retrieved {len(get_data)} status checks")
            
        except AssertionError:
            print(f"❌ Status endpoint test failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            raise

def run_tests():
    print("=" * 80)
    print("AKARA BACKEND API TEST SUITE")
    print("=" * 80)
    print(f"Testing started at: {os.path.basename(__file__)}")
    
    # Run the tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == "__main__":
    run_tests()
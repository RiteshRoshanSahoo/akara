import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Home = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedModel, setSelectedModel] = useState("bhashini");
  const [sourceLanguage, setSourceLanguage] = useState("hi");
  const [targetLanguage, setTargetLanguage] = useState("en");
  const [transcription, setTranscription] = useState("");
  const [translation, setTranslation] = useState("");
  const [translatedAudio, setTranslatedAudio] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingTime, setProcessingTime] = useState(0);
  const [error, setError] = useState("");
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [supportedLanguages, setSupportedLanguages] = useState({});
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);
  const audioRef = useRef(null);

  useEffect(() => {
    fetchSupportedLanguages();
    checkServerHealth();
  }, []);

  const checkServerHealth = async () => {
    try {
      const response = await axios.get(`${API}/health`);
      console.log("Server health:", response.data);
    } catch (error) {
      console.error("Server health check failed:", error);
    }
  };

  const fetchSupportedLanguages = async () => {
    try {
      const response = await axios.get(`${API}/transcription/languages`);
      setSupportedLanguages(response.data);
    } catch (error) {
      console.error("Failed to fetch supported languages:", error);
      // Fallback languages
      setSupportedLanguages({
        source_languages: {
          "hi": "Hindi",
          "en": "English",
          "bn": "Bengali",
          "ta": "Tamil",
          "te": "Telugu",
          "mr": "Marathi",
          "gu": "Gujarati",
          "kn": "Kannada",
          "ml": "Malayalam",
          "pa": "Punjabi",
          "ur": "Urdu",
          "or": "Odia"
        },
        target_languages: {
          "en": "English",
          "hi": "Hindi",
          "bn": "Bengali",
          "ta": "Tamil",
          "te": "Telugu",
          "mr": "Marathi",
          "gu": "Gujarati",
          "kn": "Kannada",
          "ml": "Malayalam",
          "pa": "Punjabi",
          "ur": "Urdu",
          "or": "Odia"
        }
      });
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setError("");
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
      setError("");
    }
  };

  const handleTranscribe = async () => {
    if (!selectedFile) {
      setError("Please select an audio file first");
      return;
    }

    setIsProcessing(true);
    setError("");
    setTranscription("");
    setTranslation("");
    setTranslatedAudio("");
    
    const startTime = Date.now();

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("source_language", sourceLanguage);
      formData.append("target_language", targetLanguage);
      formData.append("model_name", selectedModel);

      const response = await axios.post(`${API}/transcription/transcribe`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        timeout: 120000 // 2 minutes timeout
      });

      const endTime = Date.now();
      setProcessingTime((endTime - startTime) / 1000);

      setTranscription(response.data.transcript);
      setTranslation(response.data.translation);
      setTranslatedAudio(response.data.translated_audio);
      
    } catch (error) {
      console.error("Transcription error:", error);
      if (error.response?.status === 503) {
        setError("Bhashini API credentials not configured. Please contact administrator.");
      } else {
        setError(error.response?.data?.detail || "Failed to process audio. Please try again.");
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const playTranslatedAudio = () => {
    if (translatedAudio && audioRef.current) {
      const audioBlob = new Blob([
        new Uint8Array(atob(translatedAudio).split('').map(c => c.charCodeAt(0)))
      ], { type: 'audio/wav' });
      
      const audioUrl = URL.createObjectURL(audioBlob);
      audioRef.current.src = audioUrl;
      audioRef.current.play();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 relative overflow-hidden">
      {/* Background Images */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-900/20 via-purple-900/30 to-slate-900/40"></div>
        <div 
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `url('https://images.unsplash.com/photo-1608512532288-8f985c15345d')`,
            backgroundSize: 'cover',
            backgroundPosition: 'center'
          }}
        ></div>
        <div 
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `url('https://images.pexels.com/photos/31094109/pexels-photo-31094109.jpeg')`,
            backgroundSize: 'cover',
            backgroundPosition: 'center'
          }}
        ></div>
      </div>

      {/* Glassmorphism Overlay */}
      <div className="absolute inset-0 bg-black/10 backdrop-blur-sm z-10"></div>

      {/* Content */}
      <div className="relative z-20 min-h-screen flex flex-col">
        {/* Header */}
        <header className="p-6 flex justify-between items-center">
          {/* Hamburger Menu */}
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="p-3 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 hover:bg-white/20 transition-all duration-300"
          >
            <div className="w-6 h-6 flex flex-col justify-center items-center">
              <span className={`bg-white h-0.5 w-6 rounded-full transition-all duration-300 ${isMenuOpen ? 'rotate-45 translate-y-1' : ''}`}></span>
              <span className={`bg-white h-0.5 w-6 rounded-full transition-all duration-300 ${isMenuOpen ? 'opacity-0' : 'my-1'}`}></span>
              <span className={`bg-white h-0.5 w-6 rounded-full transition-all duration-300 ${isMenuOpen ? '-rotate-45 -translate-y-1' : ''}`}></span>
            </div>
          </button>

          {/* Team Badge */}
          <div className="hidden md:block">
            <div className="px-4 py-2 rounded-full bg-white/10 backdrop-blur-md border border-white/20">
              <p className="text-white/70 text-sm font-light">Team MOM Hackathon Presents</p>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 space-y-8">
          {/* Title - Matching Screenshot Exactly */}
          <div className="text-center space-y-4">
            <div className="md:hidden mb-4">
              <div className="px-4 py-2 rounded-full bg-white/10 backdrop-blur-md border border-white/20 inline-block">
                <p className="text-white/70 text-sm font-light">Team MOM Hackathon Presents</p>
              </div>
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-white text-center leading-tight">
              Transcribe and<br />Translate Audio
            </h1>
          </div>

          {/* Main Interface - Exactly matching screenshot layout */}
          <div className="w-full max-w-4xl grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column */}
            <div className="space-y-6">
              {/* Upload File Section - Exact match */}
              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20 hover:bg-white/15 transition-all duration-300">
                <h3 className="text-xl font-semibold text-white mb-4 text-center">Upload File</h3>
                <div
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 cursor-pointer ${
                    dragActive ? 'border-blue-400 bg-blue-400/10' : 'border-white/30 hover:border-white/50'
                  }`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="audio/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <div className="space-y-4">
                    <div className="w-16 h-16 mx-auto bg-white/20 rounded-full flex items-center justify-center">
                      <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                    <div>
                      <button className="px-6 py-3 bg-white/20 hover:bg-white/30 text-white rounded-xl font-medium transition-all duration-300">
                        Choose File
                      </button>
                      <p className="text-white/60 text-sm mt-2">
                        {selectedFile ? selectedFile.name : "No file selected"}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Select Model Section - Exact match */}
              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
                <h3 className="text-xl font-semibold text-white mb-4 text-center">Select Model</h3>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full p-3 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 text-white appearance-none focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  <option value="bhashini">Choose a model</option>
                </select>
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div>
                    <label className="block text-white/80 text-sm font-medium mb-2">Source Language</label>
                    <select
                      value={sourceLanguage}
                      onChange={(e) => setSourceLanguage(e.target.value)}
                      className="w-full p-3 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 text-white appearance-none focus:outline-none focus:ring-2 focus:ring-blue-400"
                    >
                      {Object.entries(supportedLanguages.source_languages || {}).map(([code, name]) => (
                        <option key={code} value={code}>{name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-white/80 text-sm font-medium mb-2">Target Language</label>
                    <select
                      value={targetLanguage}
                      onChange={(e) => setTargetLanguage(e.target.value)}
                      className="w-full p-3 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 text-white appearance-none focus:outline-none focus:ring-2 focus:ring-blue-400"
                    >
                      {Object.entries(supportedLanguages.target_languages || {}).map(([code, name]) => (
                        <option key={code} value={code}>{name}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <button
                  onClick={handleTranscribe}
                  disabled={!selectedFile || isProcessing}
                  className="w-full mt-6 py-3 px-6 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-xl hover:from-blue-600 hover:to-purple-700 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isProcessing ? (
                    <div className="flex items-center justify-center">
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                      Processing...
                    </div>
                  ) : (
                    "Transcribe & Translate"
                  )}
                </button>
              </div>
            </div>

            {/* Right Column */}
            <div className="space-y-6">
              {/* Transcription Display - Exact match */}
              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20 min-h-[200px]">
                <h3 className="text-xl font-semibold text-white mb-4 text-center">Transcription</h3>
                <div className="bg-white/5 rounded-xl p-4 min-h-[150px] max-h-[300px] overflow-y-auto">
                  <p className="text-white/90 leading-relaxed text-center">
                    {transcription || "The meeting today focused on project deadlines and resource allocation. The team discussed adjusting timelines and collaborating closely across departments to ensure all milestones are met efficiently."}
                  </p>
                </div>
                {processingTime > 0 && (
                  <div className="mt-4 text-white/60 text-sm text-center">
                    Processing time: {processingTime.toFixed(2)}s
                  </div>
                )}
              </div>

              {/* Translated Audio Playback - Exact match */}
              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
                <h3 className="text-xl font-semibold text-white mb-4 text-center">Translated Audio Playback</h3>
                <div className="flex items-center justify-center">
                  <button
                    onClick={playTranslatedAudio}
                    disabled={!translatedAudio}
                    className="flex items-center space-x-3 px-6 py-3 bg-white/10 backdrop-blur-md border border-white/20 rounded-xl hover:bg-white/20 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                      <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                    </div>
                    <div className="text-left">
                      <p className="text-white font-medium">Translated Audio</p>
                      <p className="text-white/60 text-sm">0:00</p>
                    </div>
                  </button>
                  <audio ref={audioRef} className="hidden" controls />
                </div>
              </div>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="w-full max-w-4xl">
              <div className="bg-red-500/20 backdrop-blur-md rounded-2xl p-4 border border-red-500/30">
                <p className="text-red-200 text-center">{error}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Side Menu */}
      {isMenuOpen && (
        <div className="fixed inset-0 z-50 flex">
          <div className="bg-black/50 backdrop-blur-sm flex-1" onClick={() => setIsMenuOpen(false)}></div>
          <div className="w-80 bg-white/10 backdrop-blur-md border-l border-white/20 p-6">
            <div className="flex justify-between items-center mb-8">
              <h2 className="text-xl font-semibold text-white">Menu</h2>
              <button
                onClick={() => setIsMenuOpen(false)}
                className="p-2 rounded-lg bg-white/10 backdrop-blur-md border border-white/20 hover:bg-white/20 transition-all duration-300"
              >
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <nav className="space-y-4">
              <a href="#" className="block p-3 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 hover:bg-white/20 transition-all duration-300">
                <div className="text-white font-medium">Home</div>
              </a>
              <a href="#" className="block p-3 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 hover:bg-white/20 transition-all duration-300">
                <div className="text-white font-medium">History</div>
              </a>
              <a href="#" className="block p-3 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 hover:bg-white/20 transition-all duration-300">
                <div className="text-white font-medium">Settings</div>
              </a>
              <a href="#" className="block p-3 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 hover:bg-white/20 transition-all duration-300">
                <div className="text-white font-medium">About</div>
              </a>
            </nav>
          </div>
        </div>
      )}
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />}>
            <Route index element={<Home />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;

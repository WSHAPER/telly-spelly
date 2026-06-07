from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
import whisper
import os
import logging
import time
from settings import Settings
logger = logging.getLogger(__name__)

class TranscriptionWorker(QThread):
    finished = pyqtSignal(str, str)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, model, audio_file, language=None):
        super().__init__()
        self.model = model
        self.audio_file = audio_file
        self.language = language
        
    def run(self):
        try:
            if not os.path.exists(self.audio_file):
                raise FileNotFoundError(f"Audio file not found: {self.audio_file}")
                
            self.progress.emit("Loading audio file...")
            
            self.progress.emit("Processing audio with Whisper...")
            result = self.model.transcribe(
                self.audio_file,
                fp16=False,
                language=self.language
            )
            
            text = result["text"].strip()
            detected_lang = result.get("language", "")
            if not text:
                raise ValueError("No text was transcribed")
                
            self.progress.emit("Transcription completed!")
            logger.info(f"Transcribed text: {text[:100]}...")
            self.finished.emit(text, detected_lang)
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            self.error.emit(f"Transcription failed: {str(e)}")
            self.finished.emit("", "")
        finally:
            try:
                if os.path.exists(self.audio_file):
                    os.remove(self.audio_file)
            except Exception as e:
                logger.error(f"Failed to remove temporary file: {e}")

class WhisperTranscriber(QObject):
    transcription_progress = pyqtSignal(str)
    transcription_finished = pyqtSignal(str, str)
    transcription_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.worker = None
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_worker)
        self._cleanup_timer.setSingleShot(True)
        self.load_model()
        
    def load_model(self):
        try:
            settings = Settings()
            model_name = settings.get('model', 'turbo')
            logger.info(f"Loading Whisper model: {model_name}")
            
            # Redirect whisper's logging to our logger
            import logging as whisper_logging
            whisper_logging.getLogger("whisper").setLevel(logging.WARNING)
            
            self.model = whisper.load_model(model_name)
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
        
    def _cleanup_worker(self):
        if self.worker:
            if self.worker.isFinished():
                self.worker.deleteLater()
                self.worker = None
                
    def transcribe_file(self, audio_file):
        if self.worker and self.worker.isRunning():
            logger.warning("Transcription already in progress")
            return
            
        settings = Settings()
        auto_detect = settings.get('auto_detect', True)
        language = None if auto_detect else settings.get('language', 'en')
            
        self.transcription_progress.emit("Starting transcription...")
            
        self.worker = TranscriptionWorker(self.model, audio_file, language=language)
        self.worker.finished.connect(self.transcription_finished)
        self.worker.progress.connect(self.transcription_progress)
        self.worker.error.connect(self.transcription_error)
        self.worker.finished.connect(lambda: self._cleanup_timer.start(1000))
        self.worker.start() 
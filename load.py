import threading
import itertools
import time
import sys
import os
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
import azure.cognitiveservices.speech.translation as speechtranslation

class SpeechClient:
    """
    Sets up Azure speech translation with push stream.
    Exposes:
      - self.recognizer
      - self.push_stream
    """
    def __init__(self, source_lang=None, target_lang=None):
        self._stop = False
        spinner = threading.Thread(target=self._spinner, daemon=True)
        spinner.start()
        try:
            load_dotenv()
            key      = os.getenv("SPEECH_KEY")
            region   = os.getenv("SPEECH_REGION")
            endpoint = os.getenv("AZURE_SPEECH_ENDPOINT")

            self.source_lang = source_lang or os.getenv("SOURCE_LANG", "zh-CN")
            self.target_lang = target_lang or os.getenv("TARGET_LANG", "en-US")

            # Configure translation service
            if endpoint:
                cfg = speechtranslation.SpeechTranslationConfig(
                    endpoint=endpoint,
                    subscription=key,
                    speech_recognition_language=self.source_lang
                )
            else:
                cfg = speechtranslation.SpeechTranslationConfig(
                    subscription=key,
                    region=region,
                    speech_recognition_language=self.source_lang
                )
            cfg.add_target_language(self.target_lang)

            # Create push stream for raw PCM
            self.push_stream = speechsdk.audio.PushAudioInputStream()
            audio_cfg = speechsdk.audio.AudioConfig(stream=self.push_stream)
            self.recognizer = speechtranslation.TranslationRecognizer(
                translation_config=cfg,
                audio_config=audio_cfg
            )
        finally:
            self._stop = True
            spinner.join()

    def _spinner(self):
        for ch in itertools.cycle("|/-\\"):
            if self._stop:
                break
            sys.stdout.write(f"\r{ch} Initializing…")
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write("\r" + " "*30 + "\r")
        sys.stdout.flush()

    def start(self):
        """Begin continuous recognition."""
        self.recognizer.start_continuous_recognition()

    def stop(self):
        """Stop continuous recognition."""
        self.recognizer.stop_continuous_recognition()


def print_default_mic():
    """Prints default microphone info."""
    import sounddevice as sd
    idx = sd.default.device[0]
    info = sd.query_devices(idx, 'input')
    print(f"🎤 Using mic #{idx}: {info['name']}")

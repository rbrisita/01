from abc import ABC, abstractmethod
import os
import platform
import shutil
import urllib.request

from source.server.services.utils import get_huggingface_model_hash, get_model_hash
from .utils import run_command

"""
Whisper STT Abstract Class
"""

class Stt(ABC):
    def __init__(self, config):
        self._service_directory = config["service_directory"]
        self._install(self._service_directory)

        model_path = os.path.join(self._service_directory, "model")
        model_file = os.getenv("WHISPER_MODEL_NAME", "ggml-tiny.en.bin")
        self._validate(model_path, model_file)

        self._model_path = model_path
        self._model_file = model_file
        self._model_file_path = os.path.join(model_path, model_file)


    @abstractmethod
    def _install(self, service_directory: str):
        pass


    def _validate(self, model_path: str, model_file: str):
        details_url = f"https://huggingface.co/ggerganov/whisper.cpp/raw/main/{model_file}"
        details_hash = get_huggingface_model_hash(details_url)

        while not self._valid_model(model_path, model_file, details_hash):
            print(f"Downloading Whisper model '{model_file}'.")
            WHISPER_MODEL_URL = os.getenv(
                "WHISPER_MODEL_URL",
                "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/",
            )
            os.makedirs(model_path, exist_ok=True)
            urllib.request.urlretrieve(
                f"{WHISPER_MODEL_URL}{model_file}",
                os.path.join(model_path, model_file),
            )
        else:
            print(f"Whisper model '{model_file}' installed.")


    def _valid_model(self, model_path: str, model_file: str, details_hash: str) -> bool:
        """
        Try to validate model through cryptographic hash comparison.
        """

        model_file_path = os.path.join(model_path, model_file)
        if not os.path.isfile(model_file_path):
            return False

        # Compare
        model_hash = get_model_hash(model_file_path)
        if details_hash == model_hash:
            print(f"Whisper model '{model_file}' file is valid.")
        else:
            msg = f"""
The model '{model_file}' did not validate. Whisper STT may not function correctly.
The model path is '{model_path}'.
Manually download and verify the model's hash to get better functionality.
Continuing.
            """
            print(msg)

        return True


    @abstractmethod
    def _transcribe(self, audio_file_path: str) -> str:
        pass


    def stt(self, audio_file_path: str) -> str:
        return self._transcribe(audio_file_path)

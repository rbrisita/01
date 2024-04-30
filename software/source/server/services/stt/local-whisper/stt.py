from abc import ABC, abstractmethod
import os
import platform
import shutil
import urllib.request
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
        # Download details file and get hash
        details_file = f"https://huggingface.co/ggerganov/whisper.cpp/raw/main/{model_file}"
        try:
            with urllib.request.urlopen(details_file) as response:
                body_bytes = response.read()
        except:
            print("Internet connection not detected. Skipping validation.")
            return True

        """
        Example output of 'https://huggingface.co/ggerganov/whisper.cpp/raw/main/ggml-tiny.en.bin':
        version https://git-lfs.github.com/spec/v1
        oid sha256:921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f
        size 77704715
        """
        lines = body_bytes.splitlines()
        colon_index = lines[1].find(b':')
        details_hash = lines[1][colon_index + 1:].decode()

        while not self._valid_model(model_path, model_file, details_hash):
            print(f"Downloading Whisper model '{model_file}'.")
            WHISPER_MODEL_URL = os.getenv(
                "WHISPER_MODEL_URL",
                "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/",
            )
            os.makedirs(self._model_path, exist_ok=True)
            urllib.request.urlretrieve(
                f"{WHISPER_MODEL_URL}{model_file}",
                os.path.join(model_path, model_file),
            )
        else:
            print(f"Whisper model '{model_file}' installed.")


    def _valid_model(self, model_path: str, model_file: str, details_hash: str) -> bool:
        # Try to validate model through cryptographic hash comparison

        model_file_path = os.path.join(model_path, model_file)
        if not os.path.isfile(model_file_path):
            return False

        # Generate model hash using native commands
        model_hash = None
        system = platform.system()
        if system == 'Darwin':
            shasum_path = shutil.which('shasum')
            model_hash = run_command(
                f"{shasum_path} -a 256 {model_file_path} | cut -d' ' -f1",
                shell=True
            )
        elif system == 'Linux':
            sha256sum_path = shutil.which('sha256sum')
            model_hash = run_command(
                f"{sha256sum_path} {model_file_path} | cut -d' ' -f1",
                shell=True
            )
        elif system == 'Windows':
            comspec = os.getenv("COMSPEC")
            if comspec.endswith('cmd.exe'): # Most likely
                certutil_path = shutil.which('certutil')
                first_op = f"{certutil_path} -hashfile {model_file_path} sha256"
                second_op = 'findstr /v "SHA256 CertUtil"' # Prints only lines that do not contain a match
                model_hash = run_command(
                    f"{first_op} | {second_op}",
                    shell=True
                )
            else:
                first_op = f"Get-FileHash -LiteralPath {model_file_path} -Algorithm SHA256"
                subsequent_ops = "Select-Object Hash | Format-Table -HideTableHeaders | Out-String"
                model_hash = run_command([
                        'pwsh',
                        '-Command',
                        f"({first_op} | {subsequent_ops}).trim().toLower()"
                    ]
                )
        else:
            print(f"System '{system}' not supported. Skipping validation.")
            return True

        # Compare
        if details_hash == model_hash.strip():
            print(f"Whisper model '{model_file}' file is valid.")
        else:
            msg = f'''
The model '{model_file}' did not validate. Whisper STT may not function correctly.
The model path is '{model_path}'.
Manually download and verify the model's hash to get better functionality.
Continuing.
            '''
            print(msg)

        return True


    @abstractmethod
    def _transcribe(self, audio_file_path: str) -> str:
        pass


    def stt(self, audio_file_path: str) -> str:
        return self._transcribe(audio_file_path)

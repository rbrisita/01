from datetime import datetime
import os
import platform
import shutil
import subprocess
import tempfile
import ffmpeg
import urllib.request
from .stt import Stt

class WhisperRust(Stt):
    def _install(self, service_directory: str):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        print('WhisperRust::_install script_dir', script_dir)
        source_whisper_rust_path = os.path.join(script_dir, "whisper-rust")
        print('WhisperRust::_install source_whisper_rust_path', source_whisper_rust_path)
        if not os.path.exists(source_whisper_rust_path):
            print(f"Source directory does not exist: {source_whisper_rust_path}")
            exit(1)

        WHISPER_RUST_PATH = os.path.join(service_directory, "whisper-rust")
        print('WhisperRust::_install WHISPER_RUST_PATH', WHISPER_RUST_PATH)
        if not os.path.exists(WHISPER_RUST_PATH):
            shutil.copytree(source_whisper_rust_path, WHISPER_RUST_PATH)
        os.chdir(WHISPER_RUST_PATH)

        # Check if whisper-rust executable exists before attempting to build
        if not os.path.isfile(
            os.path.join(WHISPER_RUST_PATH, "target/release/whisper-rust")
        ):
            # Check if Rust is installed. Needed to build whisper executable

            rustc_path = shutil.which("rustc")

            if rustc_path is None:
                print(
                    "Rust is not installed or is not in system PATH. Please install Rust before proceeding."
                )
                exit(1)

            print('WhisperRust::_install Building')
            # Build Whisper Rust executable if not found
            subprocess.run(["cargo", "build", "--release"], check=True)
        else:
            print("Whisper Rust executable already exists. Skipping build.")

        WHISPER_MODEL_PATH = os.path.join(service_directory, "model")
        WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "ggml-tiny.en.bin")
        while not self._valid_model(WHISPER_MODEL_PATH, WHISPER_MODEL_NAME):
            print(f"Downloading Whisper model '{WHISPER_MODEL_NAME}'.")
            WHISPER_MODEL_URL = os.getenv(
                "WHISPER_MODEL_URL",
                "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/",
            )
            os.makedirs(WHISPER_MODEL_PATH, exist_ok=True)
            urllib.request.urlretrieve(
                f"{WHISPER_MODEL_URL}{WHISPER_MODEL_NAME}",
                os.path.join(WHISPER_MODEL_PATH, WHISPER_MODEL_NAME),
            )
        else:
            print(f"Whisper model '{WHISPER_MODEL_NAME}' installed.")


    def _valid_model(self, model_path: str, model_file: str) -> bool:
        # Try to validate model through cryptographic hash comparison

        model_file_path = os.path.join(model_path, model_file)
        if not os.path.isfile(model_file_path):
            return False

        # Download details file and get hash
        details_file = f"https://huggingface.co/ggerganov/whisper.cpp/raw/main/{model_file}"
        try:
            with urllib.request.urlopen(details_file) as response:
                body_bytes = response.read()
        except:
            print("Internet connection not detected. Skipping validation.")
            return True

        # TODO: File example
        lines = body_bytes.splitlines()
        colon_index = lines[1].find(b':')
        details_hash = lines[1][colon_index + 1:].decode()

        # Generate model hash using native commands
        model_hash = None
        system = platform.system()
        if system == 'Darwin':
            shasum_path = shutil.which('shasum')
            model_hash = subprocess.check_output(
                f"{shasum_path} -a 256 {model_file_path} | cut -d' ' -f1",
                text=True,
                shell=True
            )
        elif system == 'Linux':
            sha256sum_path = shutil.which('sha256sum')
            model_hash = subprocess.check_output(
                f"{sha256sum_path} {model_file_path} | cut -d' ' -f1",
                text=True,
                shell=True
            )
        elif system == 'Windows':
            comspec = os.getenv("COMSPEC")
            if comspec.endswith('cmd.exe'): # Most likely
                certutil_path = shutil.which('certutil')
                first_op = f"{certutil_path} -hashfile {model_file_path} sha256"
                second_op = 'findstr /v "SHA256 CertUtil"' # Prints only lines that do not contain a match.
                model_hash = subprocess.check_output(f"{first_op} | {second_op}", text=True, shell=True)
            else:
                first_op = f"Get-FileHash -LiteralPath {model_file_path} -Algorithm SHA256"
                subsequent_ops = "Select-Object Hash | Format-Table -HideTableHeaders | Out-String"
                model_hash = subprocess.check_output([
                    'pwsh',
                    '-Command',
                    f"({first_op} | {subsequent_ops}).trim().toLower()"
                    ],
                    text=True
                )
        else:
            print(f"System '{system}' not supported. Skipping validation.")
            return True

        if details_hash == model_hash.strip():
            print(f"Whisper model '{model_file}' file is valid.")
        else:
            msg = f'''
                The model '{model_file}' did not validate. STT may not function correctly.
                The model path is '{model_path}'.
                Manually download and verify the model's hash to get better functionality.
                Continuing.
            '''
            print(msg)

        return True


    def _transcribe(self, service_directory: str, audio_file_path: str) -> str:
        wav_file_path = self._convert(audio_file_path)

        # No need to keep doing this, could be done after model validation
        local_path = os.path.join(service_directory, "model")
        model_name = os.getenv("WHISPER_MODEL_NAME", "ggml-tiny.en.bin")
        model_file_path = os.path.join(local_path, model_name)

        # This could stream, specific to Whisper Rust
        whisper_rust_path = os.path.join(
            service_directory, "whisper-rust", "target", "release"
        )

        try:
            transcription, _ = self._run_command(
                [
                    os.path.join(whisper_rust_path, "whisper-rust"),
                    "--model-path",
                    model_file_path,
                    "--file-path",
                    wav_file_path,
                ]
            )
        finally:
            os.remove(wav_file_path)

        return transcription


    # This could be a class method
    def _convert(self, audio_file_path: str) -> str:
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(
            temp_dir, f"output_stt_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.wav"
        )
        ffmpeg.input(audio_file_path).output(
            output_path, acodec="pcm_s16le", ac=1, ar="16k", loglevel="panic"
        ).run()
        return output_path

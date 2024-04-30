import os
import shutil
from .stt import Stt
from .utils import convert, remove_env_tags, run_command

class WhisperRust(Stt):
    def __init__(self, config):
        super().__init__(config)
        self._command_path = os.path.join(config["service_directory"], "whisper-rust")
        self._command_file_path = os.path.join(self._command_path, "target", "release", "whisper-rust")


    def _install(self, service_directory: str):
        # Check if whisper-rust executable exists before attempting to build
        command_path = os.path.join(service_directory, "whisper-rust")
        if os.path.isfile(
            os.path.join(command_path, "target", "release", "whisper-rust")
        ):
            print("Whisper Rust executable already exists. Skipping build.")
            return

        # Check tools needed to build whisper-rust executable
        cargo_path = shutil.which("cargo")
        if cargo_path is None:
            print(
                "Rust or Cargo are not installed or are not in system PATH. Please install Rust and Cargo with `rustup` before proceeding."
            )
            exit(1)

        # Prepare source folder
        if not os.path.exists(command_path):
            script_dir = os.path.dirname(os.path.realpath(__file__))
            source_whisper_rust_path = os.path.join(script_dir, "whisper-rust")
            if not os.path.exists(source_whisper_rust_path):
                print(f"Source directory does not exist: {source_whisper_rust_path}")
                exit(1)

            shutil.copytree(source_whisper_rust_path, command_path)

        # Build Whisper Rust executable
        run_command([
                cargo_path,
                "build",
                "--release"
            ],
            cwd=command_path
        )


    def _transcribe(self, audio_file_path: str) -> str:
        wav_file_path = convert(audio_file_path)

        try:
            transcription = run_command(
                [
                    self._command_file_path,
                    "--model-path",
                    self._model_file_path,
                    "--file-path",
                    wav_file_path,
                ]
            )
        finally:
            os.remove(wav_file_path)

        return remove_env_tags(transcription).strip()

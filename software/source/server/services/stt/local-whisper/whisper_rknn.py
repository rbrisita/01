import os
import sys
from .stt import Stt
from .utils import remove_env_tags, run_command

class WhisperRknn(Stt):
    """
    Whisper RockChip Neural Network (RKNN) class handles the installation and use of `.rknn` files on the NPU.
    """

    # Output contains template strings
    _template_end = '|>'


    def __init__(self, config):
        super().__init__(config)
        self._command_path = os.path.join(self._service_directory, "whisper-rknn")


    def _install(self, service_directory: str):
        command_path = os.path.join(service_directory, "whisper-rknn")
        if not os.path.exists(command_path):
            os.mkdir(command_path)

        # Check if whisper-rknn exists before attempting to build
        lib_path = os.path.join(command_path, "useful_transformers", "librknnrt.so")
        if os.path.isfile(lib_path):
            print("Whisper RKNN executable already exists. Skipping build.")
            return

        wheel_url = "https://github.com/usefulsensors/useful-transformers/releases/download/0.1_rk3588/useful_transformers-0.1-cp310-cp310-linux_aarch64.whl"
        run_command([
                sys.executable, # python
                "-m", "pip", "install",
                "--only-binary", ":all:",
                "--target", ".",
                wheel_url
            ],
            cwd=command_path
        )


    def _transcribe(self, audio_file_path: str) -> str:
        # Only supports `tiny.en` at the moment
        result =  run_command([
                "taskset", "-c", "4-7", # engage processor with NPU
                sys.executable, # python
                "-m", "useful_transformers.transcribe_wav",
                audio_file_path
            ],
            cwd=self._command_path
        )

        # Parse out template and environment
        te_index = result.rfind(self._template_end)
        transcription = result[te_index + len(self._template_end):]

        return remove_env_tags(transcription).strip()

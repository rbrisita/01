import os
import shutil
import subprocess
import sys
from .stt import Stt

class WhisperRknn(Stt):
    def __init__(self, config):
        self._command_path = os.path.join(config["service_directory"], "whisper-rknn")
        print('WhisperRknn::_install WHISPER_RKNN_PATH', self._command_path)
        super().__init__(config)


    def _install(self, service_directory: str):
        if not os.path.exists(self._command_path):
          script_dir = os.path.dirname(os.path.realpath(__file__))
          shutil.copytree(script_dir, self._command_path) # TODO: this is copyiinh files too

        # Check if whisper-rknn exists before attempting to build
        lib_path = os.path.join(self._command_path, "useful_transformers", "librknnrt.so")
        print('file path to shared lib', lib_path)
        print('file path to shared lib file', os.path.isfile(lib_path))
        if not os.path.isfile(lib_path):
            # TODO: Check for errors
            print('WhisperRknn::_install Installing')
            wheel_url = "https://github.com/usefulsensors/useful-transformers/releases/download/0.1_rk3588/useful_transformers-0.1-cp310-cp310-linux_aarch64.whl"
            subprocess.run([
                sys.executable, # python
                "-m", "pip", "install",
                "--only-binary", ":all:",
                "--target", ".",
                wheel_url],
                cwd=self._command_path,
                check=True
            )
        else:
            print('WhisperRknn::_install Installed')

        # TODO: download model if it doesn't exist
        # validate


    def _transcribe(self, service_directory: str, audio_file_path: str) -> str:
        # TODO: Might need to convert

        # TODO: Check for errors
        # taskset -c 4-7 python -m useful_transformers.transcribe_wav {audio_file_path}
        # run audio against command
        result =  subprocess.run([
            "taskset", "-c", "4-7", # engage NPU
            sys.executable, # python
            "-m", "useful_transformers.transcribe_wav",
            audio_file_path],
            cwd=self._command_path,
            check=True,
            text=True,
            capture_output=True
        )

        # TODO: Might have to parse out text
        print('result.stdout', result.stdout)
        print('result.stderr', result.stderr)

        return result.stdout

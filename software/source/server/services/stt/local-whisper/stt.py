from abc import ABC, abstractmethod
import subprocess

class Stt(ABC):
    def __init__(self, config):
        self.service_directory = config["service_directory"]
        self._install(self.service_directory)


    @abstractmethod
    def _install(self, service_directory: str):
        pass


    @abstractmethod
    def _transcribe(self, service_directory: str, audio_file_path: str) -> str:
        pass


    # This could be a class method, also could probably use check_output
    def _run_command(self, cmd):
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        return result.stdout, result.stderr


    def stt(self, audio_file_path) -> str:
        return self._transcribe(self.service_directory, audio_file_path)

import os
import shutil
import subprocess
import urllib.request

from interpreter import interpreter
from source.server.services.utils import get_huggingface_model_hash, get_model_hash, report_hook, run_command


class Llm:
    def __init__(self, config):
        self._interpreter = config["interpreter"]
        config.pop("interpreter", None)

        # /home/orangepi/.local/share/01/services/llm/rkllm
        self._service_directory = config["service_directory"]
        command_file_path = self._install(self._service_directory)
        print("RKLLM installed.")

        model_path = os.path.join(self._service_directory, "models")
        model_file_path = self._ensure_valid_model(model_path, self._interpreter.llm.model)

        self._command_file_path = command_file_path
        self._model_file_path = model_file_path

        self._interpreter.system_message = "You are Open Interpreter, a world-class programmer that can execute code on the user's machine."
        self._interpreter.offline = True
        self._interpreter.force_task_completion = False
        # interpreter.custom_instructions = "This is a custom instruction."

        self._interpreter.llm.context_window = 2000 # In tokens
        self._interpreter.llm.max_tokens = 1000 # In tokens
        self._interpreter.llm.supports_vision = False # Does this completions endpoint accept images?
        self._interpreter.llm.supports_functions = False # Does this completions endpoint accept/return function calls?

        self._load_model(model_file_path)


    def _install(self, service_directory: str) -> str:
        """
        Install command
        """
        command_file_path = os.path.join(service_directory, "ezrknn-llm-main", "rkllm-runtime", "example", "build", "build_linux_aarch64_Release", "rkllm")
        if os.access(command_file_path, os.F_OK | os.X_OK):
            return command_file_path

        if not os.path.exists(service_directory):
            os.makedirs(service_directory, exist_ok=True)

        # Guard against an incomplete build
        try:
            os.remove(command_file_path)
        except FileNotFoundError:
            pass

        zip_file_path = os.path.join(service_directory, "main.zip")
        if not os.access(zip_file_path, os.F_OK | os.R_OK):
            # Guard against incomplete download
            try:
                os.remove(zip_file_path)
            except FileNotFoundError:
                pass

            source_url = "https://github.com/rbrisita/ezrknn-llm/archive/refs/heads/main.zip"
            urllib.request.urlretrieve(source_url, zip_file_path, reporthook=report_hook)

        build_path = os.path.join(service_directory, "ezrknn-llm-main", "rkllm-runtime", "example")
        build_file_path = os.path.join(build_path, "build-linux.sh")
        if not os.access(build_file_path, os.F_OK | os.X_OK):
            unzip_path = shutil.which("unzip")
            subprocess.run([
                    unzip_path,
                    "-qo",  # quiet and overwrite files
                    "main.zip"
                ],
                cwd=service_directory,
                check=True
            )

        subprocess.run([
                "bash",
                "build-linux.sh"
            ],
            cwd=build_path,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        return command_file_path


    def _ensure_valid_model(self, model_path: str, model_file: str):
        # Todo: Have to get these urls from models.json file
        details_url = f"https://huggingface.co/Pelochus/qwen-1_8B-rk3588/raw/main/{model_file}"
        details_hash = get_huggingface_model_hash(details_url)

        model_file_path = os.path.join(model_path, model_file)
        while not self._valid_model(model_file_path, details_hash):
            print(f"Downloading RKLLM model '{model_file}'.")
            self._install_model(model_file_path)
        else:
            print(f"RKLLM model '{model_file}' installed.")

        return model_file_path


    def _valid_model(self, model_file_path: str, details_hash: str) -> bool:
        """
        Try to validate model through cryptographic hash comparison.
        """

        if not os.access(model_file_path, os.F_OK | os.R_OK):
            return False

        # Compare
        model_file = os.path.basename(model_file_path)
        model_path = os.path.dirname(model_file_path)
        print(f"Hashing model '{model_file}' to compare. This might take some time.")
        model_hash = get_model_hash(model_file_path)
        if details_hash == model_hash:
            print(f"RKLLM model '{model_file}' file is valid.")
        else:
            msg = f"""
The model '{model_file}' did not validate. RKNN LLM may not function correctly.
The model path is '{model_path}'.
Manually download and verify the model's hash to get better functionality.
Continuing.
            """
            print(msg)

        return True


    def _install_model(self, model_file_path: str):
        """
        Install given model to given path
        """
        model_path = os.path.dirname(model_file_path)
        if not os.path.exists(model_path):
            os.mkdir(model_path)

        # qwen-chat-1_8B.rkllm
        if not os.access(model_file_path, os.F_OK | os.R_OK):
            # Guard against an incomplete download
            try:
                os.remove(model_file_path)
            except FileNotFoundError:
                pass

            model_file = os.path.basename(model_file_path)
            model_url = f"https://huggingface.co/Pelochus/qwen-1_8B-rk3588/resolve/main/{model_file}"
            urllib.request.urlretrieve(model_url, model_file_path, reporthook=report_hook)
            print("\n")

        print(f"RKLLM model {model_file} downloaded.")


    def _load_model(self, model_file_path: str):
        cmd = [
            self._command_file_path,
            "--model", model_file_path,
            "--quiet",
            "--top_k", "1",
            "--tokens", "256"
        ]
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE
        )


    def llm(self, messages, model, stream, max_tokens):
        """
        OpenAI-compatible completions function (this one just echoes what the user said back).
        """
        users_content = messages[-1].get("content") # Get last message's content

        characters_written = 0
        process = self._process
        while True:
            if process.poll() is not None:
                # Todo: Try to load model again?
                break

            # Read a line from the subprocess's stdout
            line = process.stdout.read1().decode("utf-8")

            # Check if the line is empty, indicating that the subprocess has finished
            if not line:
                continue
            elif line.endswith(">> ") and characters_written:
                break
            elif line.endswith(">> "):
                characters_written = process.stdin.write(b"%b\n" % users_content.encode())
                process.stdin.flush()
            else:
                yield {"choices": [{"delta": {"content": line}}]}

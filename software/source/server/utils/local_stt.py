import os
import platform
import inquirer
from interpreter import interpreter

from source.server.utils.system_info import rknn_compatible


def select_local_stt():
    # Define the choices for local STTs
    choices = [
        "Whisper Rust",
    ]
    if platform.python_version().startswith("3.10") and rknn_compatible():
        choices.append("Whisper RKNN")

    if len(choices) == 1:
        return os.path.join("local-whisper", "whisper_rust")

    interpreter.display_message(
        "> 01 is compatible with several local stt providers.\n"
    )

    # Use inquirer to let the user select an option
    questions = [
        inquirer.List(
            "STT",
            message="Which one would you like to use?",
            choices=choices,
        ),
    ]
    answers = inquirer.prompt(questions)

    selected_stt = answers["STT"]

    if selected_stt == "Whisper RKNN":
        interpreter.display_message(
            """
            Selected Whisper RKNN
            """
        )
        return os.path.join("local-whisper", "whisper_rknn")

    interpreter.display_message(
        """
        Selected Whisper Rust
        """
    )
    return os.path.join("local-whisper", "whisper_rust")

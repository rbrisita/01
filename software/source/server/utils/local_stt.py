import os
import inquirer
from interpreter import interpreter
import platform


def select_local_stt():
    # START OF LOCAL STT PROVIDER LOGIC
    interpreter.display_message(
        "> 01 is compatible with several local stt providers.\n"
    )

    # Define the choices for local STTs
    choices = [
        "Whisper Rust",
    ]

    if platform.python_version().startswith("3.10"):
        if platform.system() == "Linux" and platform.machine() == "aarch64":
            if "rk3588" in platform.platform() or "rk3588" in platform.release():
                choices.append("Whisper RKNN")

    if len(choices) == 1:
        return os.path.join("local-whisper", "whisper_rust")

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

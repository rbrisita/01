import platform
import inquirer
from interpreter import interpreter


def select_local_tts():
    # Define the choices for local STTs
    choices = [
        "Piper",
    ]

    info = platform.freedesktop_os_release()
    if info["ID"] == "debian":
        choices.append("Mimic3")

    interpreter.display_message(
        "> 01 is compatible with several local tts providers.\n"
    )

    # Use inquirer to let the user select an option
    questions = [
        inquirer.List(
            "TTS",
            message="Which one would you like to use?",
            choices=choices,
        ),
    ]
    answers = inquirer.prompt(questions)

    selected_tts = answers["TTS"]

    if selected_tts == "Mimic3":
        interpreter.display_message(
            """
            Selected Mimic3
            """
        )
        return "mimic3"

    interpreter.display_message(
        """
        Selected Piper
        """
    )
    return "piper"

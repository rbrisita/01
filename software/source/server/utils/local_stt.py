import os
import sys
import subprocess
import time
import inquirer
from interpreter import interpreter
import platform


def select_local_stt():
    # START OF LOCAL STT PROVIDER LOGIC
    interpreter.display_message(
        "> 01 is compatible with several local stt providers.\n"
    )

    '''
    Check platform for specific chip set

architecture ('64bit', 'ELF')
machine aarch64
platform Linux-5.10.110-rockchip-rk3588-aarch64-with-glibc2.31
processor
release 5.10.110-rockchip-rk3588
system Linux
version #1.1.4 SMP Wed Mar 8 14:26:01 CST 2023
uname uname_result(system='Linux', node='orangepi5', release='5.10.110-rockchip-rk3588', version='#1.1.4 SMP Wed Mar 8 14:26:01 CST 2023', machine='aarch64')
python_version 3.10.10
python_build ('main', 'Mar 21 2023 18:38:58')
    '''

    print('architecture', platform.architecture())
    print('machine', platform.machine())
    print('platform', platform.platform())
    print('processor', platform.processor())
    print('release', platform.release())
    print('system', platform.system())
    # print('system_alias', platform.system_alias())
    print('version', platform.version())
    print('uname', platform.uname())
    print('python_version', platform.python_version()) # Rknn errors on 3.11+
    print('python_build', platform.python_build())
    # print('freedesktop_os_release', platform.freedesktop_os_release())

    # Define the choices for local STTs
    choices = [
        "Whisper Rust",
    ]

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

    if selected_stt == "Whisper Rust":
        interpreter.display_message(
            """
            Selected Whisper Rust
            """
        )
        return os.path.join("local-whisper", "whisper_rust")
    elif selected_stt == "Whisper RKNN":
        interpreter.display_message(
            """
            Selected Whisper RKNN
            """
        )
        return os.path.join("local-whisper", "whisper_rknn")

    return os.path.join("local-whisper", "whisper_rust")

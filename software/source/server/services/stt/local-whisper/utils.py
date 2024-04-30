
from datetime import datetime
import os
import re
import subprocess
import tempfile

import ffmpeg

env_tags = re.compile(r"[\[\(].*[\)\]]", re.MULTILINE)

def remove_env_tags(transcription: str) -> str:
    print(f'remove env from transcription: {transcription}')
    return env_tags.sub("", transcription)


def convert(audio_file_path: str) -> str:
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(
        temp_dir, f"output_stt_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.wav"
    )
    ffmpeg.input(audio_file_path).output(
        output_path, acodec="pcm_s16le", ac=1, ar="16k", loglevel="panic"
    ).run()
    return output_path


def run_command(cmd, **kwargs):
    return subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE, **kwargs)

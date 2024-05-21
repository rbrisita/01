import os
import subprocess
import tempfile
import urllib.request

import ffmpeg
from source.server.services.utils import report_hook


class Tts:
    def __init__(self, config):
        self._service_directory = config["service_directory"]
        self._command_file_path = self._install(self._service_directory)
        self._install_model(self._service_directory)
        self._load_model(self._service_directory)


    def _install(self, service_directory):
        if service_directory.endswith("mimic3"):
            command_path = service_directory
        else:
            command_path = os.path.join(service_directory, "mimic3")

        if not os.access(command_path, os.R_OK | os.W_OK):
            os.makedirs(command_path, exist_ok=True)

        deb_file_path = os.path.join(service_directory, "mimic3.deb")
        if not os.access(deb_file_path, os.F_OK | os.R_OK):
            # Guard against incomplete download
            try:
                os.remove(deb_file_path)
            except FileNotFoundError:
                pass

            print("Downloading Mimic 3 Debian Release.")
            source_url = "https://github.com/MycroftAI/mimic3/releases/download/release%2Fv0.2.4/mycroft-mimic3-tts_0.2.4_arm64.deb"
            urllib.request.urlretrieve(source_url, deb_file_path, reporthook=report_hook)
            print("\n")

        command_file_path = os.path.join(service_directory, "usr", "bin", "mimic3")
        if not os.access(command_file_path, os.F_OK | os.X_OK):
            # Guard against incomplete extraction
            try:
                os.remove("usr")
            except FileNotFoundError:
                pass

            print("Installing Mimic 3 Debian Release.")
            subprocess.run([
                    "dpkg-deb",
                    "-x", deb_file_path, "."
                ],
                check=True,
                cwd=service_directory,
            )

        return command_file_path


    def _install_model(self, service_directory):
        onnx_file_path = os.path.join(service_directory, "voices", "en_US", "vctk_low", "generator.onnx")
        if not os.access(onnx_file_path, os.F_OK | os.R_OK):
            # Guard against incomplete download
            try:
                os.remove("voices")
            except FileNotFoundError:
                pass

            print("Downloading Mimic 3 Model.")
            download_file_path = os.path.join("usr", "bin", "mimic3-download")
            subprocess.run([
                    download_file_path,
                    "--output-dir", "voices",
                    "en_US/vctk_low"
                ],
                check=True,
                cwd=service_directory,
            )

            details_file_path = os.path.join(service_directory, "voices", "en_US", "vctk_low", "lfs.details")
            os.rename(onnx_file_path, details_file_path)
            source_url = "https://huggingface.co/rbrisita/mimic3-voices/resolve/main/en_US/vctk_low/generator.onnx"
            urllib.request.urlretrieve(source_url, onnx_file_path, reporthook=report_hook)
            print("\n")


    def  _load_model(self, service_directory):
        """
        usage: mimic3_tts [-h] [--remote [REMOTE]]
                        [--stdin-format {auto,lines,document}]
                        [--voice VOICE] [--speaker SPEAKER]
                        [--voices-dir VOICES_DIR] [--voices]
                        [--output-dir OUTPUT_DIR]
                        [--output-naming {text,time,id}]
                        [--id-delimiter ID_DELIMITER] [--interactive]
                        [--csv] [--csv-delimiter CSV_DELIMITER]
                        [--csv-voice] [--mark-file MARK_FILE]
                        [--noise-scale NOISE_SCALE]
                        [--length-scale LENGTH_SCALE]
                        [--noise-w NOISE_W]
                        [--result-queue-size RESULT_QUEUE_SIZE]
                        [--process-on-blank-line] [--ssml] [--stdout]
                        [--preload-voice PRELOAD_VOICE]
                        [--play-program PLAY_PROGRAM] [--cuda]
                        [--deterministic] [--seed SEED] [--version]
                        [--debug]
                        [text ...]
        """
        print("Load Mimic 3 Model.")
        self._process = subprocess.Popen([
                self._command_file_path,
                "--voices-dir", "voices",
                "--voice", "en_US/vctk_low#1", # select speaker id 1
                "--preload-voice", "en_US/vctk_low",
                "--length-scale", "1.4", # speed of voice (default 1)
                "--csv", # allow character separated values to write file
                "--output-dir", "/tmp",
                "--interactive",
            ],
            text=True,
            cwd=service_directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE
        )


    def tts(self, text, mobile):
        print(f"tts {text}")
        _, output_file = tempfile.mkstemp()

        self._process.stdin.write(f"{output_file}|{text}\n")
        self._process.stdin.flush()

        # Wait for file to be written
        output_file += ".wav"
        while not os.path.exists(output_file):
            pass

        return output_file
        #     # TODO: hack to format audio correctly for device
        #     if mobile:
        #         outfile = tempfile.gettempdir() + "/" + "output.wav"
        #         ffmpeg.input(output_file).output(
        #             outfile, f="wav", ar="16000", ac="1", loglevel="panic"
        #         ).run()
        #     else:
        #         outfile = tempfile.gettempdir() + "/" + "raw.dat"
        #         ffmpeg.input(output_file).output(
        #             outfile, f="s16le", ar="16000", ac="1", loglevel="panic"
        #         ).run()

        # return outfile

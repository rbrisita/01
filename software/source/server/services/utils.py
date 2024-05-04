import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request


def run_command(cmd, **kwargs) -> str:
    return subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE, **kwargs)


# https://blog.shichao.io/2012/10/04/progress_speed_indicator_for_urlretrieve_in_python.html
def report_hook(count: int, block_size: int, total_size: int):
    print('report_hook count', count)
    print('report_hook block_size', block_size)
    print('report_hook total_size', total_size)

    global start_time
    if count == 0:
        start_time = time.time()
        return

    if total_size < 1:
        total_size = 1

    duration = time.time() - start_time
    progress_size = int(count * block_size)
    speed = int(progress_size / (1024 * duration))
    percent = min(int(count * block_size * 100 / total_size), 100)

    sys.stdout.write("\r...%d%%, %d MB, %d KB/s, %d seconds passed" %
                    (percent, progress_size / (1024 * 1024), speed, duration))
    sys.stdout.flush()
    print("\n")



def get_huggingface_model_hash(details_url : str) -> str | None:
    # Download details file and get hash
    try:
        with urllib.request.urlopen(details_url) as response:
            body_bytes = response.read()
    except:
        print("Internet connection not detected. Skipping validation.")
        return None

    """
    Example output of 'https://huggingface.co/ggerganov/whisper.cpp/raw/main/ggml-tiny.en.bin':
    version https://git-lfs.github.com/spec/v1
    oid sha256:921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f
    size 77704715
    """
    lines = body_bytes.splitlines()
    colon_index = lines[1].find(b':')
    details_hash = lines[1][colon_index + 1:].decode()
    return details_hash.strip()


def get_model_hash(model_file_path: str) -> str | None:
    # Generate model hash using native commands
    model_hash = ""
    system = platform.system()
    if system == "Darwin":
        shasum_path = shutil.which("shasum")
        model_hash = run_command(
            f"{shasum_path} -a 256 {model_file_path} | cut -d' ' -f1",
            shell=True
        )
    elif system == "Linux":
        sha256sum_path = shutil.which("sha256sum")
        model_hash = run_command(
            f"{sha256sum_path} {model_file_path} | cut -d' ' -f1",
            shell=True
        )
    elif system == "Windows":
        comspec = os.getenv("COMSPEC")
        if comspec.endswith("cmd.exe"): # Most likely
            certutil_path = shutil.which("certutil")
            first_op = f"{certutil_path} -hashfile {model_file_path} sha256"
            second_op = 'findstr /v "SHA256 CertUtil"' # Prints only lines that do not contain a match
            model_hash = run_command(
                f"{first_op} | {second_op}",
                shell=True
            )
        else:
            first_op = f"Get-FileHash -LiteralPath {model_file_path} -Algorithm SHA256"
            subsequent_ops = "Select-Object Hash | Format-Table -HideTableHeaders | Out-String"
            model_hash = run_command([
                    "pwsh",
                    "-Command",
                    f"({first_op} | {subsequent_ops}).trim().toLower()"
                ]
            )
    else:
        print(f"System '{system}' not supported. Skipping validation.")
        return None

    return model_hash.strip()

from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

import traceback
from platformdirs import user_data_dir
import json
import os
import datetime
from .utils.bytes_to_wav import bytes_to_wav
import re
import asyncio
from .utils.kernel import put_kernel_messages_into_queue
from .i import configure_interpreter
from interpreter import interpreter
from ..utils.accumulator import Accumulator
from .utils.logs import setup_logging
from .utils.logs import logger
import base64
from ..utils.print_markdown import print_markdown
from .queues import Queues

os.environ["STT_RUNNER"] = "server"
os.environ["TTS_RUNNER"] = "server"

markdown = """
○

*Starting...*
"""
print("")
print_markdown(markdown)
print("")


setup_logging()

accumulator_global = Accumulator()

app_dir = user_data_dir("01")
conversation_history_path = os.path.join(app_dir, "conversations", "user.json")

SERVER_LOCAL_PORT = int(os.getenv("SERVER_LOCAL_PORT", 10001))


# This is so we only say() full sentences
def is_full_sentence(text):
    return text.endswith((".", "!", "?"))


def split_into_sentences(text):
    return re.split(r"(?<=[.!?])\s+", text)

# Switch code executor to device if that's set

if os.getenv("CODE_RUNNER") == "device":
    # (This should probably just loop through all languages and apply these changes instead)

    class Python:
        # This is the name that will appear to the LLM.
        name = "python"

        def __init__(self):
            self.halt = False

        async def run(self, code):
            """Generator that yields a dictionary in LMC Format."""

            from_computer, _, to_device = Queues.get()

            # Prepare the data
            message = {
                "role": "assistant",
                "type": "code",
                "format": "python",
                "content": code,
            }

            # Unless it was just sent to the device, send it wrapped in flags
            if not (interpreter.messages and interpreter.messages[-1] == message):
                await to_device.put(
                    {
                        "role": "assistant",
                        "type": "code",
                        "format": "python",
                        "start": True,
                    }
                )
                await to_device.put(message)
                await to_device.put(
                    {
                        "role": "assistant",
                        "type": "code",
                        "format": "python",
                        "end": True,
                    }
                )

            # Stream the response
            logger.info("Waiting for the device to respond...")
            while True:
                chunk = from_computer.get()
                logger.info(f"Server received from device: {chunk}")
                if "end" in chunk:
                    break
                yield chunk

        def stop(self):
            self.halt = True

        def terminate(self):
            """Terminates the entire process."""
            # dramatic!! do nothing
            pass

    interpreter.computer.languages = [Python]

# Configure interpreter
interpreter = configure_interpreter(interpreter)


async def listener(mobile: bool):
    from_computer, from_user, to_device = Queues.get()

    while True:
        try:
            if mobile:
                accumulator_mobile = Accumulator()

            while True:
                if not from_user.empty():
                    chunk = await from_user.get()
                    break
                elif not from_computer.empty():
                    chunk = from_computer.get()
                    break
                await asyncio.sleep(1)

            if mobile:
                message = accumulator_mobile.accumulate_mobile(chunk)
            else:
                message = accumulator_global.accumulate(chunk)

            if message == None:
                # Will be None until we have a full message ready
                continue

            # print(str(message)[:1000])

            # At this point, we have our message

            if message["type"] == "audio" and message["format"].startswith("bytes"):
                if (
                    "content" not in message
                    or message["content"] == None
                    or message["content"] == ""
                ):  # If it was nothing / silence / empty
                    continue

                # Convert bytes to audio file
                # Format will be bytes.wav or bytes.opus
                mime_type = "audio/" + message["format"].split(".")[1]
                # print("input audio file content", message["content"][:100])
                audio_file_path = bytes_to_wav(message["content"], mime_type)
                # print("Audio file path:", audio_file_path)

                # For microphone debugging:
                if False:
                    os.system(f"open {audio_file_path}")
                    import time

                    time.sleep(15)

                # stt is a bound method
                text = stt(audio_file_path)
                print(f"> '{text}'")
                message = {"role": "user", "type": "message", "content": text}

            # At this point, we have only text messages

            if type(message["content"]) != str:
                print("This should be a string, but it's not:", message["content"])
                message["content"] = message["content"].decode()

            # Custom stop message will halt us
            if message["content"].lower().strip(".,! ") == "stop":
                continue

            # Load, append, and save conversation history
            with open(conversation_history_path, "r") as file:
                messages = json.load(file)
            messages.append(message)
            with open(conversation_history_path, "w") as file:
                json.dump(messages, file, indent=4)

            accumulated_text = ""

            if any(
                [m["type"] == "image" for m in messages]
            ) and interpreter.llm.model.startswith("gpt-"):
                interpreter.llm.model = "gpt-4-vision-preview"
                interpreter.llm.supports_vision = True

            for chunk in interpreter.chat(messages, stream=True, display=True):
                if any([m["type"] == "image" for m in interpreter.messages]):
                    interpreter.llm.model = "gpt-4-vision-preview"

                logger.debug("Got chunk:", chunk)

                # Send it to the user
                await to_device.put(chunk)

                # Yield to the event loop, so you actually send it out
                await asyncio.sleep(0.01)

                if os.getenv("TTS_RUNNER") == "server":
                    # Speak full sentences out loud
                    if (
                        chunk["role"] == "assistant"
                        and "content" in chunk
                        and chunk["type"] == "message"
                    ):
                        accumulated_text += chunk["content"]
                        sentences = split_into_sentences(accumulated_text)

                        # If we're going to speak, say we're going to stop sending text.
                        # This should be fixed probably, we should be able to do both in parallel, or only one.
                        if any(is_full_sentence(sentence) for sentence in sentences):
                            await to_device.put(
                                {"role": "assistant", "type": "message", "end": True}
                            )

                        if is_full_sentence(sentences[-1]):
                            for sentence in sentences:
                                await stream_tts_to_device(sentence, mobile)
                            accumulated_text = ""
                        else:
                            for sentence in sentences[:-1]:
                                await stream_tts_to_device(sentence, mobile)
                            accumulated_text = sentences[-1]

                        # If we're going to speak, say we're going to stop sending text.
                        # This should be fixed probably, we should be able to do both in parallel, or only one.
                        if any(is_full_sentence(sentence) for sentence in sentences):
                            await to_device.put(
                                {"role": "assistant", "type": "message", "start": True}
                            )

                # If we have a new message, save our progress and go back to the top
                if not from_user.empty():
                    # Check if it's just an end flag. We ignore those.
                    temp_message = await from_user.get()

                    if (
                        type(temp_message) is dict
                        and temp_message.get("role") == "user"
                        and temp_message.get("end")
                    ):
                        # Yup. False alarm.
                        continue
                    else:
                        # Whoops! Put that back
                        await from_user.put(temp_message)

                    with open(conversation_history_path, "w") as file:
                        json.dump(interpreter.messages, file, indent=4)

                    # TODO: is triggering seemingly randomly
                    # logger.info("New user message received. Breaking.")
                    # break

                # Also check if there's any new computer messages
                if not from_computer.empty():
                    with open(conversation_history_path, "w") as file:
                        json.dump(interpreter.messages, file, indent=4)

                    logger.info("New computer message received. Breaking.")
                    break
        except:
            traceback.print_exc()


async def stream_tts_to_device(sentence, mobile: bool):
    force_task_completion_responses = [
        "the task is done",
        "the task is impossible",
        "let me know what you'd like to do next",
    ]
    if sentence.lower().strip().strip(".!?").strip() in force_task_completion_responses:
        return

    for chunk in stream_tts(sentence, mobile):
        await Queues.to_device.put(chunk)


def stream_tts(sentence, mobile: bool):
    audio_file = tts(sentence, mobile)

    # Read the entire WAV file
    with open(audio_file, "rb") as f:
        audio_bytes = f.read()

    if mobile:
        file_type = "audio/wav"

        os.remove(audio_file)

        # stream the audio as a single sentence
        yield {
            "role": "assistant",
            "type": "audio",
            "format": file_type,
            "content": base64.b64encode(audio_bytes).decode("utf-8"),
            "start": True,
            "end": True,
        }

    else:
        # stream the audio in chunk sizes
        os.remove(audio_file)

        file_type = "bytes.raw"
        chunk_size = 1024

        yield {"role": "assistant", "type": "audio", "format": file_type, "start": True}
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i : i + chunk_size]
            yield chunk
        yield {"role": "assistant", "type": "audio", "format": file_type, "end": True}


from uvicorn import Config, Server
import os
from importlib import import_module


async def main(
    server_host,
    server_port,
    llm_service,
    model,
    llm_supports_vision,
    llm_supports_functions,
    context_window,
    max_tokens,
    temperature,
    tts_service,
    stt_service,
    mobile,
):
    # Setup services
    application_directory = user_data_dir("01")
    services_directory = os.path.join(application_directory, "services")

    service_dict = {"stt": stt_service, "llm": llm_service, "tts": tts_service}

    # Create a temp file with the session number
    session_file_path = os.path.join(user_data_dir("01"), "01-session.txt")
    with open(session_file_path, "w") as session_file:
        session_id = int(datetime.datetime.now().timestamp() * 1000)
        session_file.write(str(session_id))

    for service in service_dict:
        # This is the folder they can mess around in
        service_directory = os.path.join(
            services_directory, service, service_dict[service]
        )
        config = {"service_directory": service_directory}

        if service == "llm":
            config.update(
                {
                    "interpreter": interpreter,
                    "model": model,
                    "llm_supports_vision": llm_supports_vision,
                    "llm_supports_functions": llm_supports_functions,
                    "context_window": context_window,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            )
        elif service == "stt":
            # Parse stt key value
            path_parts = service_dict[service].split(os.sep)
            file_name = path_parts.pop()

            # Update config
            config.update({"service_directory": os.path.join(services_directory, service, *path_parts)})

            import_path = f".server.services.{service}.{'.'.join(path_parts)}.{file_name}"
            module = import_module(
                import_path,
                package="source",
            )

            module_parts = file_name.split("_")
            capitalized = []
            for word in module_parts:
                capitalized.append(word.capitalize())
            module_name = "".join(capitalized)

            ServiceClass = getattr(module, module_name)
            service_instance = ServiceClass(config)
            globals()[service] = getattr(service_instance, service)
            continue

        module = import_module(
            f".server.services.{service}.{service_dict[service]}.{service}",
            package="source",
        )

        ServiceClass = getattr(module, service.capitalize())
        service_instance = ServiceClass(config)
        globals()[service] = getattr(service_instance, service)

    # llm is a bound method
    interpreter.llm.completions = llm

    # Start listening
    asyncio.create_task(listener(mobile))

    # Start watching the kernel if it's your job to do that
    if True:  # in the future, code can run on device. for now, just server.
        asyncio.create_task(put_kernel_messages_into_queue(Queues.from_computer))

    config = Config(
        "source.server.app:app",
        host=server_host,
        port=int(server_port),
        lifespan="on",
        ws_ping_timeout=None,
        ws_ping_interval=None
    )
    server = Server(config)
    await server.serve()


# Run the FastAPI app
if __name__ == "__main__":
    asyncio.run(main())

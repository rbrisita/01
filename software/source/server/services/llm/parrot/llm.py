from interpreter import interpreter


class Llm:
    def __init__(self, config):
        self._interpreter = config["interpreter"]
        config.pop("interpreter", None)

        # /home/orangepi/.local/share/01/services/llm/rkllm
        self._service_directory = config["service_directory"]
        print("Parrot installed.")

        self._interpreter.system_message = "You are Open Interpreter, a world-class programmer that can execute code on the user's machine."
        self._interpreter.offline = True
        self._interpreter.force_task_completion = False
        # interpreter.custom_instructions = "This is a custom instruction."

        self._interpreter.llm.context_window = 2000 # In tokens
        self._interpreter.llm.max_tokens = 1000 # In tokens
        self._interpreter.llm.supports_vision = False # Does this completions endpoint accept images?
        self._interpreter.llm.supports_functions = False # Does this completions endpoint accept/return function calls?


    def _install(self, service_directory: str) -> str:
        pass


    def llm(self, messages, model, stream, max_tokens):
        """
        OpenAI-compatible completions function (this one just echoes what the user said back).
        """
        users_content = messages[-1].get("content") # Get last message's content

        for character in users_content:
            yield {"choices": [{"delta": {"content": character}}]}

        """
        yield {"choices": [{"role": "assistant", "type": "message", "start": True}]}

            chunk = {
                        "id": i,
                        "object": "chat.completion.chunk",
                        "created": time.time(),
                        "model": model,
                        "choices": [{"delta": {"content": character}}],
                    }
            yield chunk

        yield {"choices": [{"role": "assistant", "type": "message", "end": True}]}
        """

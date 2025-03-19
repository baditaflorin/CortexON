# File: utils/model_client.py
import os
from pydantic_ai.models.anthropic import AnthropicModel
from utils.ant_client import get_client as get_anthropic_client
from utils.ollama_client import OllamaModel
from utils.ollama_wrapper import OllamaModelWrapper

def get_model():
    ollama_url = os.getenv("OLLAMA_API_URL")
    if ollama_url:
        model_name = os.getenv("OLLAMA_MODEL_NAME", "default-ollama-model")
        ollama_instance = OllamaModel(api_url=ollama_url, model_name=model_name)
        return OllamaModelWrapper(ollama_instance)
    else:
        model_name = os.getenv("ANTHROPIC_MODEL_NAME")
        client = get_anthropic_client()
        return AnthropicModel(model_name=model_name, anthropic_client=client)

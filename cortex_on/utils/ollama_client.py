# File: utils/ollama_client.py
import os
import requests

class OllamaModel:
    def __init__(self, api_url: str, model_name: str = None):
        self.api_url = api_url
        self.model_name = model_name

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Send a POST request to your Ollama server with the prompt.
        Adjust the payload and response parsing as needed according to your Ollama server’s API.
        """
        payload = {"prompt": prompt}
        if self.model_name:
            payload["model"] = self.model_name

        response = requests.post(self.api_url, json=payload)
        response.raise_for_status()
        data = response.json()
        # Assume the Ollama server returns the generated text under the key 'completion'
        return data.get("completion", "")

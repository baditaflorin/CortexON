# File: utils/ollama_wrapper.py

class OllamaModelWrapper:
    def __init__(self, model):
        self.model = model
        # Create a string representation for model inference purposes.
        self.value = f"ollama:{model.model_name}"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

    def __getitem__(self, index):
        # Allow slicing and indexing on the internal string.
        return self.value[index]

    def __len__(self):
        return len(self.value)

    def startswith(self, prefix):
        return self.value.startswith(prefix)

    def generate(self, prompt: str, **kwargs) -> str:
        # Delegate generate calls to the underlying model.
        return self.model.generate(prompt, **kwargs)

    def __getattr__(self, attr):
        # Delegate any other attribute lookup to the underlying model.
        return getattr(self.model, attr)

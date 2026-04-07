import os
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")  # e.g., llama3

def call_ollama(prompt: str):
    url = f"{OLLAMA_HOST}/v1/completions"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "max_tokens": 300
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    data = response.json()
    # Ollama usually returns choices[0].text
    return data["choices"][0]["text"]

# Example usage
output = call_ollama("Hello Ollama, introduce yourself!")
print(output)
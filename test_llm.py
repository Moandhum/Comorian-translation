import requests

def ask_ollama(prompt):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "tinyllama",
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(url, json=payload)
    return response.json()["response"]

# Exemple d'utilisation
question = "génère une phrase en français de sentiment positif, maximum 10 mots"
réponse = ask_ollama(question)

print("🤖 TinyLlama répond :")
print(réponse)

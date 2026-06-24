import json, subprocess, sys

# Read key from config
config = json.loads(open(r"C:\Users\admin\.gamefactory\config.json").read())
api_key = config["image"]["api_key"]

# Try different image generation approaches
models = ["openai/dall-e-3", "google/gemini-3.1-flash-image"]
endpoints = ["/v1/images/generations", "/v1/chat/completions"]

for model in models:
    for ep in endpoints:
        url = "https://openrouter.ai/api" + ep
        headers = {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}
        if "images" in ep:
            body = {"model": model, "prompt": "pixel cat", "n": 1, "size": "1024x1024"}
        else:
            body = {"model": model, "messages": [{"role": "user", "content": "Generate a pixel art cat sprite"}], "max_tokens": 100}
        
        try:
            import requests
            resp = requests.post(url, headers=headers, json=body, timeout=30)
            print(f"{model} via {ep}: HTTP {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            print(f"{model} via {ep}: Error - {e}")
        print()

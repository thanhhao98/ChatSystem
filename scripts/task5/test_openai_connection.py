import os
import sys
from openai import OpenAI

def load_env():
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    os.environ[k] = v

def main():
    load_env()
    key = os.environ.get("OPENAI_API_KEY", "")
    base = os.environ.get("OPENAI_BASE_URL", "")
    
    # If base url contains placeholder, remove it so it uses standard api.openai.com
    if "<" in base or "gateway" in base:
        os.environ.pop("OPENAI_BASE_URL", None)
        base = None

    if not key or key.startswith("<"):
        print("ERROR: OPENAI_API_KEY is missing or is still a placeholder.")
        sys.exit(1)

    print(f"Connecting to OpenAI with key prefix: {key[:8]}...")
    try:
        client = OpenAI(api_key=key, base_url=base or None)
        models = client.models.list()
        first_few = [m.id for m in list(models)[:3]]
        print("SUCCESS! Connected to OpenAI successfully. Sample models:", first_few)
    except Exception as e:
        print("FAILED to connect to OpenAI:", type(e).__name__, e)
        sys.exit(2)

if __name__ == "__main__":
    main()

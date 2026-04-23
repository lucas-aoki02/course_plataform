import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# Load .env
env_path = Path('C:/Users/Lucas Aoki/.gemini/antigravity/scratch/course_platform/.env')
load_dotenv(env_path)

key = os.getenv("GROQ_API_KEY")
print(f"Key found: {key[:10]}...{key[-5:] if key else ''}")

client = Groq(api_key=key)

try:
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "Hello",
            }
        ],
        model="llama-3.1-8b-instant",
    )
    print("Success!")
    print(chat_completion.choices[0].message.content)
except Exception as e:
    print(f"Failed: {e}")

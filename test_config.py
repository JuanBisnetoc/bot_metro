import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("CHAT_ID")

print(f"Token: {token}")
print(f"Chat ID: {chat_id}")
print(f"Token vazio? {token is None}")
print(f"Chat ID vazio? {chat_id is None}")

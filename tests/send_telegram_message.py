import os
import requests


TOKEN = "8850763968:AAEkL6lOqUGxGWATjfXZ3RUTWPn7GS_Ffr0"
CHAT_ID = "-5261796237"

url = (
    f"https://api.telegram.org"
    f"/bot{TOKEN}/sendMessage"
)

payload = {
    "chat_id": CHAT_ID,
    "text": "🔥 Teste de notificação"
}

response = requests.post(
    url,
    data=payload
)

print(response.json())
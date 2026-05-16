import requests

INSTANCE_ID = (
    ""
)

TOKEN = (
    ""
)

url = (
    "https://7107.api.greenapi.com"
    f"/waInstance{INSTANCE_ID}"
    "/sendMessage"
    f"/{TOKEN}"
)

payload = {
    "chatId": (
        ""
    ),
    "message": (
        "🔥 Teste WhatsApp API"
    )
}

response = requests.post(
    url,
    json=payload
)

print(response.status_code)
print(response.text)
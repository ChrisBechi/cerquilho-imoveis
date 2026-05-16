from dotenv import load_dotenv
import os

load_dotenv()

CHECK_INTERVAL_MINUTES = int(
    os.getenv("CHECK_INTERVAL_MINUTES", 30)
)

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(
    os.getenv("EMAIL_PORT", 587)
)

EMAIL_USERNAME = os.getenv(
    "EMAIL_USERNAME"
)

EMAIL_PASSWORD = os.getenv(
    "EMAIL_PASSWORD"
)

EMAIL_TO = os.getenv(
    "EMAIL_TO"
)

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID"
)
TELEGRAM_BOT_TOKEN= os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

GREEN_API_URL = os.getenv(
    "GREEN_API_URL"
)

GREEN_API_INSTANCE_ID = os.getenv(
    "GREEN_API_INSTANCE_ID"
)

GREEN_API_TOKEN = os.getenv(
    "GREEN_API_TOKEN"
)

WHATSAPP_CHAT_ID = os.getenv(
    "WHATSAPP_CHAT_ID"
)

SUPABASE_URL = os.getenv(
    "SUPABASE_URL"
)

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY"
)
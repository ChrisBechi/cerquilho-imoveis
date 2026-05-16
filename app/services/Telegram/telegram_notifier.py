import requests

from app.config.settings import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID
)
from app.utils.price_utils import format_price


class TelegramNotifier:

    BASE_URL = (
        "https://api.telegram.org"
    )

    def send_new_listing(
        self,
        listing
    ):

        caption = f"""
🔥 <b>NOVO IMÓVEL</b>

🏠 <b>{listing["title"]}</b>

💰 <b>{listing["price_label"]}</b>

🛏️ Quartos: {listing["bedrooms"]} | 🛁 Banheiros: {listing["bathrooms"]}

📡 Imobiliária: {listing["provider"]}
        """

        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": (
                            "🔗 Ver imóvel"
                        ),

                        "url":
                            listing["url"]
                    }
                ]
            ]
        }

        try:

            thumbnail_url = (
                listing.get(
                    "thumbnail_url"
                )
            )

            # ==============================
            # FOTO
            # ==============================

            if thumbnail_url:

                url = (
                    f"{self.BASE_URL}"
                    f"/bot{TELEGRAM_BOT_TOKEN}"
                    "/sendPhoto"
                )

                payload = {

                    "chat_id":
                        TELEGRAM_CHAT_ID,

                    "photo":
                        thumbnail_url
                        .split("?")[0],

                    "caption":
                        caption,

                    "parse_mode":
                        "HTML",

                    "reply_markup":
                        keyboard
                }

                response = requests.post(

                    url,

                    json=payload,

                    timeout=30
                )

            # ==============================
            # TEXTO
            # ==============================

            else:

                url = (
                    f"{self.BASE_URL}"
                    f"/bot{TELEGRAM_BOT_TOKEN}"
                    "/sendMessage"
                )

                payload = {

                    "chat_id":
                        TELEGRAM_CHAT_ID,

                    "text":
                        caption,

                    "parse_mode":
                        "HTML",

                    "reply_markup":
                        keyboard
                }

                response = requests.post(

                    url,

                    json=payload,

                    timeout=30
                )

            response.raise_for_status()

            print(
                "Telegram enviado."
            )

        except Exception as error:

            print(error)

    # =========================================
    # TEMPORARIAMENTE DESABILITADO
    # =========================================

    def send_price_change(
            self,
            item
    ):

        listing = item["listing"]

        old_price = item["old_price"]

        new_price = item["new_price"]

        is_lower = item["is_lower"]

        icon = (
            "📉"
            if is_lower
            else "📈"
        )

        status = (
            "BARATEOU"
            if is_lower
            else "FICOU MAIS CARO"
        )

        caption = f"""
{icon} <b>ALTERAÇÃO DE PREÇO</b>

🏠 <b>{listing["title"]}</b>

🔥 <b>{status}</b>

💸 De: <s>{format_price(old_price)}</s>
💰 Para: <b>{format_price(new_price)}</b>

🛏️ Quartos: {listing["bedrooms"]} | 🛁 Banheiros: {listing["bathrooms"]}

📡 Imobiliária: {listing["provider"]}
    """

        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text":
                            "🔗 Ver imóvel",

                        "url":
                            listing["url"]
                    }
                ]
            ]
        }

        try:

            thumbnail_url = (
                listing.get(
                    "thumbnail_url"
                )
            )

            # ==================================
            # FOTO
            # ==================================

            if thumbnail_url:

                url = (
                    f"{self.BASE_URL}"
                    f"/bot{TELEGRAM_BOT_TOKEN}"
                    "/sendPhoto"
                )

                payload = {

                    "chat_id":
                        TELEGRAM_CHAT_ID,

                    "photo":
                        thumbnail_url
                        .split("?")[0],

                    "caption":
                        caption,

                    "parse_mode":
                        "HTML",

                    "reply_markup":
                        keyboard
                }

                response = requests.post(

                    url,

                    json=payload,

                    timeout=30
                )

            # ==================================
            # TEXTO
            # ==================================

            else:

                url = (
                    f"{self.BASE_URL}"
                    f"/bot{TELEGRAM_BOT_TOKEN}"
                    "/sendMessage"
                )

                payload = {

                    "chat_id":
                        TELEGRAM_CHAT_ID,

                    "text":
                        caption,

                    "parse_mode":
                        "HTML",

                    "reply_markup":
                        keyboard
                }

                response = requests.post(

                    url,

                    json=payload,

                    timeout=30
                )

            response.raise_for_status()

            print(
                "Telegram alteração enviado."
            )

        except Exception as error:

            print(error)
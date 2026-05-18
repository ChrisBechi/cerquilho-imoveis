import time

import requests

from app.config.settings import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from app.utils.price_utils import format_price


class TelegramNotifier:
    BASE_URL = "https://api.telegram.org"
    MIN_SECONDS_BETWEEN_MESSAGES = 1.2
    MAX_RETRIES = 3

    def __init__(self):
        self.last_request_at = 0.0

    def wait_for_rate_limit(self):
        elapsed = time.monotonic() - self.last_request_at
        remaining = self.MIN_SECONDS_BETWEEN_MESSAGES - elapsed

        if remaining > 0:
            time.sleep(remaining)

    def post_with_retry(
        self,
        method: str,
        payload: dict,
    ) -> requests.Response | None:
        url = (
            f"{self.BASE_URL}"
            f"/bot{TELEGRAM_BOT_TOKEN}"
            f"/{method}"
        )

        for attempt in range(1, self.MAX_RETRIES + 1):
            self.wait_for_rate_limit()

            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=30,
                )
                self.last_request_at = time.monotonic()
            except Exception as error:
                print(
                    f"[TELEGRAM ERROR] method={method} attempt={attempt} "
                    f"error={error}"
                )
                return None

            if response.status_code != 429:
                try:
                    response.raise_for_status()
                except Exception as error:
                    print(
                        f"[TELEGRAM ERROR] method={method} status={response.status_code} "
                        f"error={error}"
                    )
                    return response

                return response

            retry_after = self.get_retry_after(response)
            print(
                f"[TELEGRAM RATE LIMITED] method={method} attempt={attempt} "
                f"retry_after={retry_after}s"
            )
            time.sleep(retry_after)

        print(
            f"[TELEGRAM SKIPPED] method={method} retries_exhausted=true"
        )
        return None

    @staticmethod
    def get_retry_after(
        response: requests.Response,
    ) -> int:
        try:
            payload = response.json()
        except ValueError:
            return 5

        parameters = payload.get("parameters") or {}
        retry_after = parameters.get("retry_after", 5)

        try:
            return max(1, int(retry_after))
        except (TypeError, ValueError):
            return 5

    @staticmethod
    def clean_photo_url(
        thumbnail_url: str | None,
    ) -> str | None:
        if not thumbnail_url:
            return None

        if thumbnail_url.startswith("data:"):
            return None

        return thumbnail_url.split("?")[0]

    def send_payload(
        self,
        caption: str,
        keyboard: dict,
        thumbnail_url: str | None,
        success_message: str,
    ):
        photo_url = self.clean_photo_url(
            thumbnail_url
        )

        if photo_url:
            photo_response = self.post_with_retry(
                "sendPhoto",
                {
                    "chat_id": TELEGRAM_CHAT_ID,
                    "photo": photo_url,
                    "caption": caption,
                    "parse_mode": "HTML",
                    "reply_markup": keyboard,
                },
            )

            if photo_response and photo_response.ok:
                print(success_message)
                return

            print(
                "[TELEGRAM FALLBACK] sendPhoto failed; sending text message"
            )

        message_response = self.post_with_retry(
            "sendMessage",
            {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": caption,
                "parse_mode": "HTML",
                "reply_markup": keyboard,
            },
        )

        if message_response and message_response.ok:
            print(success_message)

    def send_new_listing(
        self,
        listing,
    ):
        caption = f"""
<b>NOVO IMOVEL</b>

<b>{listing["title"]}</b>

<b>{listing["price_label"]}</b>

Quartos: {listing["bedrooms"]} | Banheiros: {listing["bathrooms"]}

Imobiliaria: {listing["provider"]}
        """

        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "Ver imovel",
                        "url": listing["url"],
                    }
                ]
            ]
        }

        self.send_payload(
            caption=caption,
            keyboard=keyboard,
            thumbnail_url=listing.get("thumbnail_url"),
            success_message="Telegram enviado.",
        )

    def send_price_change(
        self,
        item,
    ):
        listing = item["listing"]
        old_price = item["old_price"]
        new_price = item["new_price"]
        is_lower = item["is_lower"]

        status = (
            "BARATEOU"
            if is_lower
            else "FICOU MAIS CARO"
        )

        caption = f"""
<b>ALTERACAO DE PRECO</b>

<b>{listing["title"]}</b>

<b>{status}</b>

De: <s>{format_price(old_price)}</s>
Para: <b>{format_price(new_price)}</b>

Quartos: {listing["bedrooms"]} | Banheiros: {listing["bathrooms"]}

Imobiliaria: {listing["provider"]}
        """

        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "Ver imovel",
                        "url": listing["url"],
                    }
                ]
            ]
        }

        self.send_payload(
            caption=caption,
            keyboard=keyboard,
            thumbnail_url=listing.get("thumbnail_url"),
            success_message="Telegram alteracao enviado.",
        )

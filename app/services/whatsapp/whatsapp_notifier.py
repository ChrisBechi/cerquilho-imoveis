import urllib.parse
import requests

from app.config.settings import (
    GREEN_API_URL,
    GREEN_API_INSTANCE_ID,
    GREEN_API_TOKEN,
    WHATSAPP_CHAT_ID
)

from app.utils.price_utils import format_price


class WhatsAppNotifier:

    # =========================================
    # SEND NEW LISTING
    # =========================================

    def send_new_listing(
        self,
        listing
    ):

        caption = f"""
🔥 *NOVO IMÓVEL*

🏠 *{listing["title"]}*

💰 *{listing["price_label"]}*

🛏️ Quartos: {listing["bedrooms"]} | 🛁 Banheiros: {listing["bathrooms"]}

📡 Imobiliária: {listing["provider"]}
"""

        thumbnail_url = (
            listing.get(
                "thumbnail_url"
            )
        )

        if thumbnail_url:

            self.send_image(

                thumbnail_url,

                caption
            )

        else:

            self.send_message(
                caption
            )

        self.send_interactive_buttons(
            listing
        )

    # =========================================
    # SEND PRICE CHANGE
    # =========================================

    def send_price_change(
        self,
        item
    ):

        listing = item["listing"]

        old_price = int(
            item["old_price"] or 0
        )

        new_price = int(
            item["new_price"] or 0
        )

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
{icon} *ALTERAÇÃO DE PREÇO*

🏠 *{listing["title"]}*

🔥 *{status}*

💸 De: ~{format_price(old_price)}~
💰 Para: *{format_price(new_price)}*

🛏️ Quartos: {listing["bedrooms"]} | 🛁 Banheiros: {listing["bathrooms"]}

📡 Imobiliária: {listing["provider"]}
"""

        thumbnail_url = (
            listing.get(
                "thumbnail_url"
            )
        )

        if thumbnail_url:

            self.send_image(

                thumbnail_url,

                caption
            )

        else:

            self.send_message(
                caption
            )

        self.send_interactive_buttons(
            listing
        )

    # =========================================
    # SEND INTERACTIVE BUTTONS
    # =========================================

    def send_interactive_buttons(
            self,
            listing
    ):

        message = (
            f"Olá, fiquei interessado no imóvel com o código "
            f"'{listing['code']}' "
            f"e gostaria de agendar uma visita. Pode ser para o primeiro horario que tiver disponivel."
        )

        encoded_message = urllib.parse.quote(
            message
        )

        whatsapp_url = (
            f"https://wa.me/55{listing['contact']}"
            f"?text={encoded_message}"
        )

        url = (

            f"{GREEN_API_URL}"

            f"/waInstance"

            f"{GREEN_API_INSTANCE_ID}"

            "/sendInteractiveButtons"

            f"/{GREEN_API_TOKEN}"
        )

        payload = {

            "chatId":
                WHATSAPP_CHAT_ID,

            "body":
                "👇 Escolha uma opção",

            "footer":
                " ",

            "buttons": [

                {
                    "buttonId":
                        "view_listing",

                    "buttonText":
                        "🏠 Ver imóvel",

                    "type":
                        "url",

                    "url":
                        listing["url"]
                },

                {
                    "buttonId":
                        "schedule_visit",

                    "buttonText":
                        "📞 Agendar visita",

                    "type":
                        "url",

                    "url":
                        whatsapp_url
                }
            ]
        }

        response = requests.post(

            url,

            json=payload,

            timeout=30
        )

        print(response.status_code)

        print(response.text)

        response.raise_for_status()

        print(
            "WhatsApp botões enviados."
        )

    # =========================================
    # SEND MESSAGE
    # =========================================

    def send_message(
        self,
        message: str
    ):

        url = (

            f"{GREEN_API_URL}"

            f"/waInstance"

            f"{GREEN_API_INSTANCE_ID}"

            "/sendMessage"

            f"/{GREEN_API_TOKEN}"
        )

        payload = {

            "chatId":
                WHATSAPP_CHAT_ID,

            "message":
                message
        }

        response = requests.post(

            url,

            json=payload,

            timeout=30
        )

        response.raise_for_status()

        print(
            "WhatsApp texto enviado."
        )

    # =========================================
    # SEND IMAGE
    # =========================================

    def send_image(
        self,
        image_url: str,
        caption: str
    ):

        url = (

            f"{GREEN_API_URL}"

            f"/waInstance"

            f"{GREEN_API_INSTANCE_ID}"

            "/sendFileByUrl"

            f"/{GREEN_API_TOKEN}"
        )

        payload = {

            "chatId":
                WHATSAPP_CHAT_ID,

            "urlFile":
                image_url,

            "fileName":
                "imovel.jpg",

            "caption":
                caption
        }

        response = requests.post(

            url,

            json=payload,

            timeout=30
        )

        response.raise_for_status()

        print(
            "WhatsApp imagem enviada."
        )

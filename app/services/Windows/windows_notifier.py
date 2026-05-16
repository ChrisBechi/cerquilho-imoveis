import platform
import tempfile

import requests

from app.utils.price_utils import format_price


if platform.system() == "Windows":

    from winotify import Notification

else:

    Notification = None


class WindowsNotifier:

    def download_image(
        self,
        url: str
    ):

        try:

            response = requests.get(

                url,

                timeout=30
            )

            response.raise_for_status()

            temp_file = tempfile.NamedTemporaryFile(

                delete=False,

                suffix=".jpg"
            )

            temp_file.write(
                response.content
            )

            temp_file.close()

            return temp_file.name

        except Exception as error:

            print(
                f"Erro imagem: {error}"
            )

            return None

    # =========================================
    # NEW LISTING
    # =========================================

    def send_new_listing(
        self,
        listing
    ):

        if platform.system() != "Windows":

            print(
                "Windows notification ignorada."
            )

            return

        image_path = None

        thumbnail_url = (
            listing.get(
                "thumbnail_url"
            )
        )

        if thumbnail_url:

            image_path = (

                self.download_image(
                    thumbnail_url
                )
            )

        toast = Notification(

            app_id=(
                "Alerta Imóveis"
            ),

            title=(
                "🔥 Novo imóvel"
            ),

            msg=(

                f"{listing['title']}\n"

                f"{listing['price_label']}\n"

                f"\nImobiliária: "
                f"{listing['provider']}\n"
            ),

            duration="long",

            icon=image_path
        )

        toast.add_actions(

            label="Ver imóvel",

            launch=listing["url"]
        )

        toast.show()

        print(
            "Toast enviado."
        )

    def send_price_change(
        self,
        item
    ):

        if platform.system() != "Windows":

            print(
                "Windows notification ignorada."
            )

            return

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
            "Barateou"
            if is_lower
            else "Mais caro"
        )

        image_path = None

        thumbnail_url = (
            listing.get(
                "thumbnail_url"
            )
        )

        if thumbnail_url:

            image_path = (

                self.download_image(
                    thumbnail_url
                )
            )

        toast = Notification(

            app_id=(
                "Alerta Imóveis"
            ),

            title=(
                f"{icon} {status}"
            ),

            msg=(

                f"{listing['title']}\n"

                f"{format_price(old_price)}"

                f" → "

                f"{format_price(new_price)}\n"

                f"\nImobiliária: "
                f"{listing['provider']}\n"
            ),

            duration="long",

            icon=image_path
        )

        toast.add_actions(

            label="Ver imóvel",

            launch=listing["url"]
        )

        toast.show()

        print(
            "Toast alteração enviado."
        )
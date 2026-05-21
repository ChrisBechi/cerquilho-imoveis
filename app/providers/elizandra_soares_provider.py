import os
import requests
import re
from datetime import datetime
from dotenv import load_dotenv
from app.models.property_listing import PropertyListing
from app.providers.base_provider import BaseProvider


load_dotenv()


class ElizandraProvider(BaseProvider):
    NAME = "Elizandra Soares"

    BASE_URL = os.getenv(
        "ELIZANDRA_BASE_URL",
        "https://oqgfopcdzwbgmfpnbroo.supabase.co/rest/v1/properties"
    )

    API_KEY = os.getenv(
        "ELIZANDRA_API_KEY",
        ""
    )

    # =========================================
    # GET PROVIDER PHONE
    # =========================================

    def get_provider_phone(
            self
    ) -> str:

        try:

            response = requests.get(

                "https://oqgfopcdzwbgmfpnbroo.supabase.co/rest/v1/site_settings",

                headers=self.headers,

                params={
                    "select": "*"
                },

                timeout=30
            )

            response.raise_for_status()

            items = response.json()

            for item in items:

                if item.get("key") == "contactWhatsApp":
                    phone = item.get(
                        "value",
                        ""
                    )

                    normalized_phone = re.sub(
                        r"\D",
                        "",
                        phone
                    )

                    return normalized_phone

            return ""

        except Exception as error:

            print(
                f"Erro buscando telefone provider: {error}"
            )

            return ""


    @classmethod
    def _get_headers(cls):
        """Dinamicamente constrói headers com credenciais seguras"""
        if not cls.API_KEY:
            raise RuntimeError(
                "ELIZANDRA_API_KEY não configurado. "
                "Adicione à variável de ambiente."
            )
        
        return {
            "apikey": cls.API_KEY,
            "Authorization": f"Bearer {cls.API_KEY}",
            "Accept": "application/json",
            "Origin": "https://www.elizandrasoares.com.br",
            "Referer": "https://www.elizandrasoares.com.br/",
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/148.0.0.0 "
                "Safari/537.36"
            )
        }

    @property
    def headers(self):
        """Property que retorna headers dinamicamente"""
        return self._get_headers()

    def parse_listing(
            self,
            item,
            provider_phone: str
    ):
        image_urls = item.get("images", [])

        thumbnail_url = ""

        if image_urls:
            thumbnail_url = image_urls[0]

        price_label = item.get("price", "")

        if price_label and price_label != "A Consultar":
            price_label = f"R$ {price_label}"

        date_str = "2026-04-17T13:35:03.687034+00:00"

        formatted_date = datetime.fromisoformat(
            date_str
        ).strftime("%d/%m/%Y %H:%M")

        return PropertyListing(
            provider=self.NAME,
            contact=provider_phone[2:],
            area=item.get("area", ""),
            code=item.get(
                "code",
                ""
            ),
            title=item.get(
                "title",
                ""
            ).strip(),
            price_label=price_label,
            bedrooms=int(
                item.get(
                    "bedrooms",
                    0
                )
            ),
            bathrooms=int(
                item.get(
                    "bathrooms",
                    0
                )
            ),
            property_type=item.get(
                "category",
                ""
            ),
            published_at=formatted_date,
            url=(
                f"https://www.elizandrasoares.com.br/imovel/{item.get('id', '')}"
            ),
            thumbnail_url=thumbnail_url,
            image_urls=image_urls
        )

    def fetch_listings(self):
        response = requests.get(
            self.BASE_URL,
            headers=self.headers,
            params={
                "select": "*",
                "order": "created_at.desc",
                "status": "eq.Aluguel",
                "category": "eq.Casa",
                "location_city": "ilike.*cerquilho*",
                "is_private": "eq.false",
            },
            timeout=30
        )

        response.raise_for_status()

        items = response.json()

        print(
            f"Encontrados: {len(items)}"
        )

        provider_phone = (
            self.get_provider_phone()
        )

        listings = []

        for item in items:
            try:

                listing = self.parse_listing(
                    item,
                    provider_phone
                )

                self.persist_listing(
                    listing
                )

            except Exception as error:

                print(
                    f"Erro parsing: {error}"
                )

                continue

            listings.append(
                listing
            )

        return listings

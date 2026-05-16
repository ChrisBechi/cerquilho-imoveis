import requests
from datetime import datetime
from app.models.property_listing import PropertyListing
from app.providers.base_provider import BaseProvider


class ElizandraProvider(BaseProvider):
    NAME = "Elizandra Soares"

    BASE_URL = (
        "https://oqgfopcdzwbgmfpnbroo"
        ".supabase.co/rest/v1/properties"
    )

    API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9xZ2ZvcGNkendiZ21mcG5icm9vIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ2NTE2NjAsImV4cCI6MjA5MDIyNzY2MH0.DLxCWrd7zC7g_5GM047tvQNLf04F5jG0f26RhDKf0Jo"

    HEADERS = {
        "apikey": API_KEY,
        "Authorization": (
            f"Bearer {API_KEY}"
        ),
        "Accept": "application/json",
        "Origin": (
            "https://www.elizandrasoares.com.br"
        ),
        "Referer": (
            "https://www.elizandrasoares.com.br/"
        ),
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/148.0.0.0 "
            "Safari/537.36"
        )
    }

    def parse_listing(self, item):
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
            headers=self.HEADERS,
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

        listings = []

        for item in items:
            try:

                listing = self.parse_listing(
                    item
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

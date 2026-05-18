import requests

from app.models.property_listing import (
    PropertyListing
)

from app.providers.base_provider import (
    BaseProvider
)


class ScudelerProvider(
    BaseProvider
):

    NAME = "Scudeler"

    API_URL = (
        "https://www.imobiliariascudeler.com.br"
        "/api/imoveis"
    )

    HEADERS = {
        "Referer": (
            "https://www.imobiliariascudeler.com.br/"
            "alugar-imoveis/casas/cerquilho"
            "?operacao=aluguel&tipoId=10&cidade=Cerquilho&ordem=3&limite=40&idimob=1"
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

    def parse_listing(
            self,
            item
    ):

        tipo = {}

        if item.get("Tipo"):
            tipo = item["Tipo"][0]

        image_urls = []

        fotos = item.get(
            "Fotos",
            []
        )

        for foto in fotos:

            url = foto.get(
                "Foto_Media"
            )

            if url:
                image_urls.append(
                    url
                )

        thumbnail_url = ""

        if image_urls:
            thumbnail_url = image_urls[0]

        price_label = str(
            tipo.get(
                "Valor",
                ""
            )
        )

        return PropertyListing(
            provider=self.NAME,
            code=str(
                item.get(
                    "Codigo",
                    ""
                )
            ),
            title=item.get(
                "Nome",
                ""
            ),
            price_label=price_label,
            bedrooms=int(
                tipo.get(
                    "Dormitorios",
                    0
                )
            ),
            bathrooms=int(
                item.get(
                    "Banheiros",
                    0
                )
            ),
            property_type=tipo.get(
                "Categoria",
                ""
            ),
            published_at=item.get(
                "DataPublicacao",
                ""
            ),
            url=item.get(
                "URL",
                ""
            ),
            thumbnail_url=thumbnail_url,
            image_urls=image_urls
        )

    def fetch_listings(self):

        listings = []

        page = 1

        last_page = 1

        while page <= last_page:

            print(
                f"Coletando página {page}"
            )

            response = requests.get(
                self.API_URL,
                params={
                    "operacao": "aluguel",
                    "tipoId": "10",
                    "cidade": "Cerquilho",
                    "page": page,
                    "ordem": 3,
                    "limite": 40,
                    "idimob": 1,
                },
                headers=self.HEADERS,
                timeout=30
            )

            response.raise_for_status()

            payload = response.json()

            last_page = payload[
                "meta"
            ][
                "last_page"
            ]

            items = payload[
                "data"
            ]

            print(
                f"Encontrados: {len(items)}"
            )

            for item in items:

                try:

                    listing = (
                        self.parse_listing(
                            item
                        )
                    )

                    self.persist_listing(
                        listing
                    )

                    listings.append(
                        listing
                    )

                except Exception as error:

                    print(
                        f"Erro parsing: {error}"
                    )

            page += 1

        return listings
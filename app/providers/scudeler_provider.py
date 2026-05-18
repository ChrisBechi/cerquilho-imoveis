import cloudscraper

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

    CF_CLEARANCE = (
        "5_5IFX9mUqJ8dceNQxEp6zOFpsTK0eobwD_j7aGQWx8-1779075708-1.2.1.1-"
        "BspMZ4S7MdFmCEfjtJ.ifUtfTL1muOny45fM_LOnHhNLjdE4S7NAajv_5QFL."
        "CepZEm1fI0eML_762lMuFPXF7zCGecboiQVkDjCSyN.lEsqwZr9cauMAgtt5C5PXYx"
        "GyVyEIMLoN4kid5F0Lt7WBLms1rcAur3SMeqTEogbyFuySMxwH6qBUpRhQ7SwBv5_"
        "Zu5uhYEqVgZOuLybPOR1i18fC38pPZihNmJJcB5AW5xVrfNZGpCwqtKcOn3qH3t4Fl."
        "iy_IyoEV9jq_Xh9ctSjO5.0_KkQMy7yNgIfdX0hY4KVV6PVHGZBCyLiukP2PKhGXj"
        "MzuOA3woHDZemApE2Q"
    )

    HEADERS = {
        "Accept": (
            "application/json, text/plain, */*"
        ),
        "Accept-Language": (
            "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
        ),
        "Connection": (
            "keep-alive"
        ),
        "Origin": (
            "https://www.imobiliariascudeler.com.br"
        ),
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
            "Chrome/126.0.0.0 "
            "Safari/537.36"
        )
    }

    REQUEST_TIMEOUT = 60

    def __init__(self):
        super().__init__()

        self.session = cloudscraper.create_scraper(
            browser={
                "browser": "chrome",
                "platform": "windows",
                "mobile": False,
            }
        )

        self.session.headers.update(
            self.HEADERS
        )

        self.session.cookies.set(
            "cf_clearance",
            self.CF_CLEARANCE,
            domain=".imobiliariascudeler.com.br"
        )

        print(
            "[SCUDELER CF TEST] cf_clearance manual aplicado "
            "domain=.imobiliariascudeler.com.br"
        )

    def fetch_api_page(
        self,
        page: int
    ):
        params = {
            "operacao": "aluguel",
            "tipoId": "10",
            "cidade": "Cerquilho",
            "page": page,
            "ordem": 3,
            "limite": 40,
            "idimob": 1,
        }

        print(
            f"[SCUDELER CF TEST] request start page={page}"
        )

        response = self.session.get(
            self.API_URL,
            params=params,
            headers=self.HEADERS,
            timeout=self.REQUEST_TIMEOUT
        )

        print(
            f"[SCUDELER CF TEST] status={response.status_code} "
            f"reason={response.reason}"
        )

        print(
            "[SCUDELER CF TEST] response_partial="
            f"{response.text[:500]}"
        )

        if response.status_code == 403:
            print(
                "[SCUDELER CF TEST] cf_clearance manual não foi suficiente"
            )

        response.raise_for_status()
        return response

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

            response = (
                self.fetch_api_page(
                    page
                )
            )

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

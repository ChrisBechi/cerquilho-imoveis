import random
import time

import cloudscraper
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

    HOME_URL = (
        "https://www.imobiliariascudeler.com.br"
    )

    API_URL = (
        "https://www.imobiliariascudeler.com.br"
        "/api/imoveis"
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
        "Cache-Control": (
            "no-cache"
        ),
        "Origin": (
            "https://www.imobiliariascudeler.com.br"
        ),
        "Pragma": (
            "no-cache"
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

    RETRY_STATUS_CODES = {
        403,
        429
    }

    RETRY_BACKOFF_SECONDS = [
        2,
        4,
        8
    ]

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

        self.prewarmed = False

    def human_delay(
        self
    ):
        delay = random.uniform(
            2,
            5
        )

        print(
            f"[SCUDELER HUMAN DELAY] sleep={delay:.2f}s"
        )

        time.sleep(
            delay
        )

    def prewarm_session(
        self
    ):
        if self.prewarmed:
            return

        print(
            f"[SCUDELER PREWARM START] url={self.HOME_URL}"
        )

        start = time.monotonic()

        try:
            response = self.session.get(
                self.HOME_URL,
                headers={
                    **self.HEADERS,
                    "Accept": (
                        "text/html,application/xhtml+xml,"
                        "application/xml;q=0.9,image/avif,image/webp,"
                        "image/apng,*/*;q=0.8"
                    ),
                    "Referer": self.HOME_URL,
                },
                timeout=self.REQUEST_TIMEOUT
            )

            elapsed = time.monotonic() - start

            print(
                f"[SCUDELER PREWARM END] status={response.status_code} "
                f"reason={response.reason} elapsed={elapsed:.2f}s "
                f"cookies={len(self.session.cookies)}"
            )

            response.raise_for_status()
            self.prewarmed = True
            self.human_delay()

        except (
            requests.Timeout,
            requests.ConnectionError,
            requests.HTTPError
        ) as error:
            elapsed = time.monotonic() - start

            print(
                f"[SCUDELER PREWARM FAILED] "
                f"elapsed={elapsed:.2f}s error={type(error).__name__}: {error}"
            )

            raise

    def fetch_api_page(
        self,
        page: int
    ):
        self.prewarm_session()

        params = {
            "operacao": "aluguel",
            "tipoId": "10",
            "cidade": "Cerquilho",
            "page": page,
            "ordem": 3,
            "limite": 40,
            "idimob": 1,
        }

        last_error = None
        last_response = None
        max_attempts = (
            len(self.RETRY_BACKOFF_SECONDS)
            + 1
        )

        for attempt in range(1, max_attempts + 1):
            self.human_delay()

            print(
                f"[SCUDELER REQUEST START] page={page} "
                f"attempt={attempt} timeout={self.REQUEST_TIMEOUT}"
            )

            start = time.monotonic()

            try:
                response = self.session.get(
                    self.API_URL,
                    params=params,
                    headers=self.HEADERS,
                    timeout=self.REQUEST_TIMEOUT
                )
                last_response = response
                elapsed = time.monotonic() - start

                print(
                    f"[SCUDELER REQUEST END] page={page} "
                    f"attempt={attempt} status={response.status_code} "
                    f"reason={response.reason} elapsed={elapsed:.2f}s "
                    f"cookies={len(self.session.cookies)}"
                )

                if response.status_code not in self.RETRY_STATUS_CODES:
                    response.raise_for_status()
                    return response

                last_error = requests.HTTPError(
                    f"{response.status_code} response from Scudeler API"
                )

                if attempt == max_attempts:
                    break

                delay = self.RETRY_BACKOFF_SECONDS[
                    attempt - 1
                ]

                print(
                    f"[SCUDELER REQUEST RETRY] page={page} "
                    f"attempt={attempt} status={response.status_code} "
                    f"reason={response.reason} "
                    f"sleep={delay}s"
                )

            except (
                requests.Timeout,
                requests.ConnectionError
            ) as error:
                last_error = error
                elapsed = time.monotonic() - start

                if attempt == max_attempts:
                    break

                delay = self.RETRY_BACKOFF_SECONDS[
                    attempt - 1
                ]

                print(
                    f"[SCUDELER REQUEST RETRY] page={page} "
                    f"attempt={attempt} error={type(error).__name__} "
                    f"elapsed={elapsed:.2f}s sleep={delay}s"
                )

            time.sleep(
                delay
            )

        print(
            f"[SCUDELER REQUEST FAILED] page={page} "
            f"error={last_error}"
        )

        if (
            last_response is not None
            and last_response.status_code in self.RETRY_STATUS_CODES
        ):
            print(
                "[SCUDELER PLAYWRIGHT READY] cloudscraper still blocked; "
                "future fallback can be enabled here if needed"
            )

        if last_response is not None:
            last_response.raise_for_status()

        if last_error:
            raise last_error

        raise RuntimeError(
            "Scudeler request failed without an explicit error"
        )

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

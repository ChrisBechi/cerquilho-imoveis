import requests
import re
from urllib.parse import quote

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

    DETAIL_API_URL = "https://www.imobiliariascudeler.com.br/api/imovel"

    @staticmethod
    def extract_image_urls(photos) -> list[str]:
        if isinstance(photos, dict):
            groups = [photos.get("Apresentacao", [])]
            groups.extend(value for key, value in photos.items()
                          if key != "Apresentacao" and isinstance(value, list))
        elif isinstance(photos, list):
            groups = [photos]
        else:
            return []

        urls = []
        for group in groups:
            if not isinstance(group, list):
                continue
            for photo in group:
                if not isinstance(photo, dict):
                    continue
                url = (photo.get("Foto_Media") or photo.get("Foto_Grande")
                       or photo.get("Foto_Pequena"))
                if isinstance(url, str) and url.strip() and url.strip() not in urls:
                    urls.append(url.strip())
        return urls

    def fetch_listing_images(self, listing_id, company_id=1) -> list[str] | None:
        try:
            response = self.session.get(
                f"{self.DETAIL_API_URL}/{quote(str(listing_id), safe='')}",
                params={"rede": 0, "idimob": company_id},
                headers=self.HEADERS,
                timeout=30,
            )
            response.raise_for_status()
            detail = response.json().get("data")
            if not isinstance(detail, dict) or str(detail.get("ID")) != str(listing_id):
                raise ValueError("Unexpected property detail response")

            images = self.extract_image_urls(detail.get("Fotos"))
            if not images:
                raise ValueError("Property detail returned an empty gallery")

            print(f"[SCUDELER GALLERY] id={listing_id} images={len(images)}")
            return images
        except (requests.RequestException, ValueError, TypeError, AttributeError) as error:
            print(f"[SCUDELER GALLERY FAILED] id={listing_id} error={error}; "
                  "preserving saved gallery for the next run")
            return None

    WHATSAPP_API_URL = (
        "https://www.imobiliariascudeler.com.br"
        "/api/controle-whatsapp"
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

    # =========================================
    # GET PROVIDER PHONE
    # =========================================

    def get_provider_phone(
        self
    ) -> str:

        try:

            response = requests.get(

                self.WHATSAPP_API_URL,

                params={
                    "pagina": "home",
                    "idimob": 1,
                    "rede": 0
                },

                headers=self.HEADERS,

                timeout=30
            )

            response.raise_for_status()

            payload = response.json()

            phone = (

                payload
                .get('ConfWhats', {})
                .get("Usuario", {})
                .get("Fone", "")
            )

            return re.sub(
                r"\D",
                "",
                phone
            )

        except Exception as error:

            print(
                f"Erro buscando telefone: {error}"
            )

            return ""

    # =========================================
    # PARSE LISTING
    # =========================================

    def parse_listing(
        self,
        item,
        provider_phone: str
    ):

        tipo = {}

        if item.get("Tipo"):
            tipo = item["Tipo"][0]

        preview_urls = self.extract_image_urls(item.get("Fotos", []))
        gallery_urls = self.fetch_listing_images(
            item.get("ID") or item.get("Codigo"),
            item.get("Idimob") or 1,
        )
        image_urls = gallery_urls if gallery_urls is not None else preview_urls

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
            area=int(
                float(
                    item.get(
                        "AreaTotal",
                        "0"
                    ).replace(
                        ".",
                        ""
                    ).replace(
                        ",",
                        "."
                    )
                )
            ),
            contact=provider_phone,
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
            image_urls=image_urls,
            image_urls_complete=gallery_urls is not None,
        )

    # =========================================
    # FETCH LISTINGS
    # =========================================

    def fetch_listings(self):

        listings = []

        page = 1

        last_page = 1

        provider_phone = (
            self.get_provider_phone()
        )

        print(
            f"Telefone provider: {provider_phone}"
        )

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
                            item,
                            provider_phone
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

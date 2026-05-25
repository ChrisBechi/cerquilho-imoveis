import re

from bs4 import BeautifulSoup

from app.models.property_listing import PropertyListing
from app.providers.base_provider import BaseProvider

class RRProvider(BaseProvider):

    NAME = "R&R Imobiliária"

    BASE_URL = (
        "https://rrimoveiscerquilho.com.br/pesquisar-imoveis"
    )

    FILTER_URL = ("?status=locacao&location%5B%5D=cerquilho&type%5B%5D=residencial")

    def extract_area(
        self,
        soup
    ) -> int:

        meta_blocks = soup.select(
            ".rh_prop_card__meta"
        )

        for block in meta_blocks:

            title = block.select_one(
                ".rh_meta_titles"
            )

            if not title:
                continue

            label = title.get_text(
                strip=True
            ).lower()

            if "área" not in label:
                continue

            figure = block.select_one(
                ".figure"
            )

            if not figure:
                return 0

            value = figure.get_text(
                strip=True
            )

            digits = "".join(
                filter(
                    str.isdigit,
                    value
                )
            )

            if digits:
                return int(digits)

        return 0

    def extract_provider_phone(
            self,
            soup
    ) -> str:

        try:

            whatsapp_link = soup.select_one(
                'a[href*="phone="]'
            )

            if not whatsapp_link:
                return ""

            href = whatsapp_link.get(
                "href",
                ""
            )

            match = re.search(
                r"phone=\+?(\d+)",
                href
            )

            if not match:
                return ""

            phone = match.group(1)

            if phone.startswith("55"):
                phone = phone[2:]

            return phone

        except Exception as error:

            print(
                f"Erro extraindo telefone: {error}"
            )

            return ""

    def fetch_listing_images(
            self,
            listing_url: str
    ) -> list[str]:

        try:

            html = self.fetch_page(
                listing_url
            )

            soup = BeautifulSoup(
                html,
                "lxml"
            )

            images = []

            gallery_images = soup.select(
                "a.slider-img"
            )

            print(
                f"Imagens encontradas: {len(gallery_images)}"
            )

            for image in gallery_images:

                src = image.get("href")

                if not src:
                    continue

                if src not in images:
                    images.append(src)

            return images

        except Exception as error:

            print(
                f"Erro ao buscar imagens: {error}"
            )

            return []

    def extract_price_from_title(
            self,
            title: str
    ) -> str:
        """
        Extrai o valor monetário do título.
        Exemplo: "Imóvel Residencial no Bairro CECAP -Locação R$ 1.500,00"
        Retorna: "R$ 1.500,00"
        """
        match = re.search(
            r"R\$\s*[\d.,]+",
            title
        )
        return match.group(0) if match else ""

    def extract_price_value(
            self,
            price_label: str
    ) -> float:
        """
        Extrai o valor numérico do rótulo de preço.
        Interpreta formatos brasileiros como 300.000 ou 1.500,00 corretamente.
        """
        normalized = re.sub(
            r"[^\d.,]",
            "",
            price_label
        )

        if not normalized:
            return 0.0

        if "," in normalized:
            # Formato brasileiro: 1.500,00 ou 300.000,00
            normalized = normalized.replace(".", "")
            normalized = normalized.replace(",", ".")
        else:
            # Se só houver pontos, eles podem ser separadores de milhar
            normalized = normalized.replace(".", "")

        try:
            return float(normalized)
        except ValueError:
            return 0.0

    def parse_listing_element(
            self,
            element,
            contact
    ):

        code = element.get(
            "data-rh-id",
            ""
        )

        title_element = element.select_one(
            ".rh_list_card__map_details h3 a"
        )

        title = title_element.get_text(
            strip=True
        )

        url = title_element["href"]

        price_element = element.select_one(
            ".rh_list_card__price .price"
        )

        price_label = (
            price_element.get_text(
                separator=" ",
                strip=True
            )
            .replace("\xa0", " ")
            if price_element
            else ""
        )

        # Validação: se preço > 100k e há valor no título, substitui pelo valor do título
        price_value = self.extract_price_value(
            price_label
        )

        if price_value > 100000:
            price_from_title = self.extract_price_from_title(
                title
            )
            if price_from_title:
                price_label = price_from_title

        figures = element.select(
            ".rh_prop_card__meta .figure"
        )

        bedrooms = 0

        bathrooms = 0

        if len(figures) >= 1:
            bedrooms = int(
                figures[0].get_text(
                    strip=True
                )
            )

        if len(figures) >= 2:
            bathrooms = int(
                figures[1].get_text(
                    strip=True
                )
            )

        property_type = (
            "Residencial"
        )

        thumbnail_element = element.select_one(
            ".post_thumbnail"
        )

        thumbnail_url = ""

        if thumbnail_element:

            style = thumbnail_element.get(
                "style",
                ""
            )

            match = re.search(
                r"url\(['\"]?(.*?)['\"]?\)",
                style
            )

            if match:
                thumbnail_url = match.group(1)

        image_urls = self.fetch_listing_images(
            url
        )

        area = self.extract_area(
            element
        )

        return PropertyListing(
            provider=self.NAME,
            code=code,
            area=area,
            title=title,
            contact=contact,
            price_label=price_label,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            property_type=property_type,
            published_at="",
            url=url,
            thumbnail_url=thumbnail_url,
            image_urls=image_urls
        )

    def get_total_pages(self, soup):

        pagination = soup.select(
            ".rh_pagination a"
        )

        pages = []

        for item in pagination:

            text = item.get_text(
                strip=True
            )

            if text.isdigit():
                pages.append(
                    int(text)
                )

        if not pages:
            return 1

        return max(pages)

    def fetch_listings(self):
        listings = []

        first_page_html = (
            self.fetch_page(
                f"{self.BASE_URL}/{self.FILTER_URL}"
            )
        )

        soup = BeautifulSoup(
            first_page_html,
            "lxml"
        )

        total_pages = (
            self.get_total_pages(
                soup
            )
        )

        print(
            f"Total páginas: {total_pages}"
        )

        for page in range(
                1,
                total_pages + 1
        ):
            if page == 1:
                url = f"{self.BASE_URL}/{self.FILTER_URL}"
            else:
                url = (
                    f"{self.BASE_URL}/page/{page}/{self.FILTER_URL}"
                )

            print(
                f"Coletando página {page}"
            )

            html = self.fetch_page(url)

            soup = BeautifulSoup(
                html,
                "lxml"
            )

            elements = soup.select(
                "article.rh_list_card"
            )

            print(
                f"Encontrados: {len(elements)}"
            )

            contact = self.extract_provider_phone(soup)

            for element in elements:

                try:

                    listing = (
                        self.parse_listing_element(
                            element,
                            contact
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
                        f"Erro: {error}"
                    )

        return listings

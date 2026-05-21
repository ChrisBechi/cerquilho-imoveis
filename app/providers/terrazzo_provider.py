import re

from bs4 import BeautifulSoup

from app.models.property_listing import PropertyListing
from app.providers.base_provider import BaseProvider

class TerrazzoProvider(BaseProvider):

    NAME = "Terrazzo Imobiliária"

    BASE_URL = (
        "https://terrazzoimobiliaria.com.br/site/search-results"
    )

    FILTER_URL = ("?type%5B%5D=residential&status%5B%5D=aluguel")

    def extract_provider_phone(
            self,
            soup
    ) -> str:
        try:
            phone_link = soup.select_one(
                'a[href^="tel:"]'
            )

            if not phone_link:
                return ""

            href = phone_link.get(
                "href",
                ""
            )

            phone = href.replace(
                "tel:",
                ""
            )

            phone = re.sub(
                r"\D",
                "",
                phone
            )

            if phone.startswith("55"):
                phone = phone[2:]

            return phone

        except Exception as error:

            print(
                f"Erro extraindo telefone: {error}"
            )

            return ""

    def extract_area(
            self,
            element
    ) -> int:

        try:

            area_element = element.select_one(
                ".h-area .hz-figure"
            )

            if not area_element:
                return 0

            value = area_element.get_text(
                strip=True
            )

            digits = "".join(
                filter(
                    str.isdigit,
                    value
                )
            )

            return int(
                digits or 0
            )

        except Exception as error:

            print(
                f"Erro extraindo área: {error}"
            )

            return 0


    def get_total_pages(self, html: str) -> int:

        soup = BeautifulSoup(html, "lxml")

        links = soup.select(
            ".pagination-wrap a.page-link"
        )

        pages = []

        for link in links:

            href = link.get("href", "")

            match = re.search(
                r"/page/(\d+)/",
                href
            )

            if match:
                pages.append(
                    int(match.group(1))
                )

        if not pages:
            return 1

        return max(pages)

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

            gallery_links = soup.select(
                ".hs-gallery-v4-grid a"
            )

            print(
                f"Galeria encontrada: {len(gallery_links)}"
            )

            for link in gallery_links:

                src = link.get("data-src")

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

    def parse_listing_element(self, element, contact) -> PropertyListing:
        title_element = element.select_one(
            ".item-title a"
        )

        title = (
            title_element.get_text(
                " ",
                strip=True
            )
            if title_element
            else ""
        )

        url = title_element["href"]

        code = ""

        code_match = re.search(
            r"c[oó]d[\s\.\-:]*?(\d+)",
            title,
            re.IGNORECASE
        )

        if code_match:

            code = code_match.group(1)

        else:

            url_match = re.search(
                r"cod[-_/]?(\d+)",
                url,
                re.IGNORECASE
            )

            if url_match:
                code = url_match.group(1)

        if not code:
            code = url

        price_element = element.select_one(".item-price")

        price_label = (
            price_element.get_text(strip=True)
            if price_element
            else ""
        )

        beds_element = element.select_one(".h-beds .hz-figure")

        bedrooms = (
            int(beds_element.get_text(strip=True))
            if beds_element
            else 0
        )

        baths_element = element.select_one(".h-baths .hz-figure")

        bathrooms = (
            int(baths_element.get_text(strip=True))
            if baths_element
            else 0
        )

        type_element = element.select_one(".h-type span")

        property_type = (
            type_element.get_text(strip=True)
            if type_element
            else ""
        )

        date_element = element.select_one(".item-date")

        published_at = (
            date_element.get_text(strip=True)
            if date_element
            else ""
        )

        thumbnail_element = element.select_one(
            ".listing-thumb img"
        )

        thumbnail_url = ""

        if thumbnail_element:
            thumbnail_url = (
                    thumbnail_element.get("data-src")
                    or ""
            )

        image_urls = self.fetch_listing_images(
            url
        )

        area = self.extract_area(element)

        return PropertyListing(
            area=area,
            provider=self.NAME,
            contact=contact,
            code=code,
            title=title,
            price_label=price_label,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            property_type=property_type,
            published_at=published_at,
            url=url,
            thumbnail_url=thumbnail_url,
            image_urls=image_urls
        )

    def parse_page(self, html: str):

        soup = BeautifulSoup(html, "lxml")

        listings = []

        results_container = soup.select_one(
            "div.listing-view.list-view.row.gy-4.gx-4"
        )

        if not results_container:
            print("Container de resultados não encontrado.")

            return []

        items = results_container.select(
            ".item-listing-wrap"
        )

        print(f"Itens válidos encontrados: {len(items)}")

        contact = self.extract_provider_phone(
            soup)

        for item in items:

            try:

                listing = self.parse_listing_element(item, contact)

                self.persist_listing(
                    listing
                )

                listings.append(listing)

            except Exception as error:

                print(f"Erro ao parsear anúncio: {error}")

        return listings

    def build_page_url(self, page: int) -> str:

        if page == 1:
            return f"{self.BASE_URL}/{self.FILTER_URL}"

        return (f"{self.BASE_URL}/page/{page}/{self.FILTER_URL}")

    def fetch_listings(self):

        first_page_html = self.fetch_page(
            self.build_page_url(1)
        )

        total_pages = self.get_total_pages(
            first_page_html
        )

        all_listings = []

        for page in range(1, total_pages + 1):

            print(f"Coletando página {page}...")

            html = self.fetch_page(
                self.build_page_url(page)
            )

            listings = self.parse_page(html)

            all_listings.extend(listings)

        return all_listings

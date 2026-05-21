import re

from bs4 import BeautifulSoup

from app.models.property_listing import (
    PropertyListing
)

from app.providers.base_provider import (
    BaseProvider
)


class DrAdinhoProvider(
    BaseProvider
):

    NAME = "Doutor Adinho"

    BASE_URL = (
        "https://doutoradinho.com.br"
    )

    FILTER_URL = (
        "?ct_ct_status=aluguel"
        "&ct_property_type=casa"
        "&ct_city=cerquilho"
        "&ct_mls"
        "&search-listings=true"
        "&ct_community=0"
        "&ct_beds=0"
        "&ct_price_from"
        "&ct_price_to"
        "&ct_sqft_from"
        "&ct_sqft_to"
        "&ct_orderby=dateDESC"
    )

    def extract_area(
            self,
            element
    ) -> int:

        try:

            area_element = element.select_one(
                ".row.lotsize .right"
            )

            if not area_element:
                return 0

            value = area_element.get_text(
                strip=True
            )

            digits = re.sub(
                r"\D",
                "",
                value
            )

            return int(
                digits or 0
            )

        except Exception as error:

            print(
                f"Erro extraindo área: {error}"
            )

            return 0

    def extract_provider_phone(
            self,
            soup
    ) -> str:

        try:

            whatsapp_link = soup.select_one(
                'a[href*="wa.me/"]'
            )

            if not whatsapp_link:
                return ""

            href = whatsapp_link.get(
                "href",
                ""
            )

            match = re.search(
                r"wa\.me/(\d+)",
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
                "#carousel .slides li img"
            )

            print(
                f"Imagens encontradas: {len(gallery_images)}"
            )

            for image in gallery_images:

                src = image.get("data-src")

                if not src:
                    continue

                if src not in images:
                    images.append(src)

            return images

        except Exception as error:

            print(
                f"Erro buscando imagens: {error}"
            )

            return []

    def fetch_listings(self):

        listings = []

        first_page_html = self.fetch_page(
            f"{self.BASE_URL}/{self.FILTER_URL}"
        )

        first_soup = BeautifulSoup(
            first_page_html,
            "lxml"
        )

        total_pages = self.get_total_pages(
            first_soup
        )

        print(
            f"Total páginas: {total_pages}"
        )

        contact = self.extract_provider_phone(first_soup)

        for page in range(
                1,
                total_pages + 1
        ):

            if page == 1:

                url = (
                    f"{self.BASE_URL}/{self.FILTER_URL}"
                )

            else:

                url = (
                    f"{self.BASE_URL}/page/{page}/{self.FILTER_URL}"
                )

            print(
                f"Coletando página {page}"
            )

            html = self.fetch_page(
                url
            )

            soup = BeautifulSoup(
                html,
                "lxml"
            )

            elements = soup.select(
                "li.listing"
            )

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
                        f"Erro parsing: {error}"
                    )

        return listings

    def get_total_pages(
            self,
            soup
    ) -> int:

        pagination_links = soup.select(
            ".pagination a"
        )

        pages = []

        for link in pagination_links:

            href = link.get(
                "href",
                ""
            )

            match = re.search(
                r"/page/(\\d+)/",
                href
            )

            if match:

                pages.append(
                    int(
                        match.group(1)
                    )
                )

        if not pages:
            return 1

        return max(pages)

    def parse_listing_element(
            self,
            element,
            contact
    ) -> PropertyListing:

        title_element = element.select_one(
            ".grid-listing-info h5 a"
        )

        title = title_element.get_text(
            strip=True
        )

        url = title_element["href"]

        code = None

        url_match = re.search(
            r"(\d+)/?$",
            url
        )

        if url_match:

            code = url_match.group(1)

        prices = element.select(
            ".price .listing-price"
        )

        price_label = ""

        if prices:

            price_label = prices[-1].get_text(
                strip=True
            )

        beds_element = element.select_one(
            "li.beds .right"
        )

        bedrooms = (

            int(
                beds_element.get_text(
                    strip=True
                )
            )

            if beds_element
            else 0
        )

        baths_element = element.select_one(
            "li.baths .right"
        )

        bathrooms = (

            int(
                baths_element.get_text(
                    strip=True
                )
            )

            if baths_element
            else 0
        )

        type_element = element.select_one(
            "li.property-type .right"
        )

        property_type = (

            type_element.get_text(
                strip=True
            )

            if type_element
            else ""
        )

        thumbnail_element = element.select_one(
            ".listing-featured-image img"
        )

        thumbnail_url = ""

        if thumbnail_element:

            thumbnail_url = (
                thumbnail_element.get(
                    "data-src"
                )
                or ""
            )

        image_urls = self.fetch_listing_images(
            url
        )

        area = self.extract_area(element)

        return PropertyListing(
            provider=self.NAME,
            contact=contact,
            area=area,
            code=code,
            title=title,
            price_label=price_label,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            property_type=property_type,
            published_at="",
            url=url,
            thumbnail_url=thumbnail_url,
            image_urls=image_urls
        )

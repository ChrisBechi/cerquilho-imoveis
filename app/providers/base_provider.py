import requests

from abc import ABC
from abc import abstractmethod

from app.services.listing_service import ListingsService
from app.utils.price_utils import extract_price_value


class BaseProvider(ABC):
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0 Safari/537.36"
        )
    }

    def __init__(self):
        self.session = requests.Session()

        self.session.headers.update(
            self.HEADERS
        )

    def fetch_page(
        self,
        url: str
    ) -> str:

        response = self.session.get(
            url,
            headers=self.HEADERS,
            timeout=30
        )

        response.raise_for_status()

        return response.text

    def normalize_code(
        self,
        code,
        url: str
    ) -> str:

        normalized_code = str(
            code or ""
        ).strip()

        if normalized_code:
            return normalized_code

        return url

    def build_listing_payload(
        self,
        listing
    ) -> dict:

        image_urls = (
            listing.image_urls
            or []
        )

        current_price = extract_price_value(
            listing.price_label
        )

        return {
            "provider":
                self.NAME,

            "code":
                self.normalize_code(
                    listing.code,
                    listing.url
                ),

            "title":
                listing.title,

            "price_label":
                listing.price_label,

            "current_price":
                int(current_price),

            "neighborhood":
                listing.neighborhood or "",

            "bedrooms":
                int(listing.bedrooms or 0),

            "bathrooms":
                int(listing.bathrooms or 0),

            "area":
                int(listing.area or 0),

            "thumbnail_url":
                listing.thumbnail_url or "",

            "image_urls":
                list(image_urls),

            "url":
                listing.url,
        }

    def persist_listing(
        self,
        listing
    ) -> dict:

        payload = self.build_listing_payload(
            listing
        )

        print(
            f"Payload -> provider={payload.get('provider')} "
            f"code={payload.get('code')} "
            f"price_label='{payload.get('price_label')}' "
            f"current_price={payload.get('current_price')} "
            f"images={len(payload.get('image_urls', []))}"
        )

        ListingsService.upsert_listing(
            payload
        )

        return payload

    @abstractmethod
    def fetch_listings(self):
        pass

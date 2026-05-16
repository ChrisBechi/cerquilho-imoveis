from dataclasses import dataclass

@dataclass
class PropertyListing:
    provider: str
    code: str
    title: str
    price_label: str
    bedrooms: int
    bathrooms: int
    property_type: str
    published_at: str
    url: str
    thumbnail_url: str = ""
    image_urls: list[str] | None = None
    parking_spots: int = 0
    area: int = 0
    neighborhood: str = ""

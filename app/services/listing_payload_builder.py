from app.config.supabase import (
    supabase
)


class ListingPayloadBuilder:

    @staticmethod
    def build(
        listing_id: int
    ):

        listing_response = (

            supabase

            .table("listings")

            .select("*")

            .eq(
                "id",
                listing_id
            )

            .single()

            .execute()
        )

        listing = (
            listing_response.data
        )

        images_response = (

            supabase

            .table("listing_images")

            .select("image_url")

            .eq(
                "listing_id",
                listing_id
            )

            .execute()
        )

        image_urls = [

            item["image_url"]

            for item in images_response.data
        ]

        return {

            "id":
                listing["id"],

            "provider":
                listing["provider"],

            "title":
                listing["title"],

            "code":
                listing[
                    "code"
                ],

            "neighborhood":
                listing[
                    "neighborhood"
                ],

            "price":
                ListingPayloadBuilder
                .format_price(
                    listing[
                        "current_price"
                    ]
                ),

            "price_label":
                listing[
                    "price_label"
                ],

            "current_price":
                listing[
                    "current_price"
                ],

            "bedrooms":
                listing["bedrooms"],

            "bathrooms":
                listing["bathrooms"],

            "area":
                listing["area"],

            "thumbnail_url":
                listing[
                    "thumbnail_url"
                ],

            "image_urls":
                image_urls,

            "url":
                listing["url"]
        }

    @staticmethod
    def format_price(
        value: int
    ):

        return (

            f"R$ {(value / 100):,.2f}"

            .replace(",", "X")

            .replace(".", ",")

            .replace("X", ".")
        )

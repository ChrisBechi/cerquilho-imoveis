from app.config.supabase import (
    supabase
)


class ListingsService:

    @staticmethod
    def normalize_price(
        value
    ) -> int:

        return int(
            value or 0
        )

    @staticmethod
    def sync_images(
        listing_id: int,
        image_urls: list[str]
    ):

        if not image_urls:
            return

        existing = (

            supabase

            .table("listing_images")

            .select("image_url")

            .eq(
                "listing_id",
                listing_id
            )

            .execute()
        )

        existing_urls = {

            item["image_url"]

            for item in existing.data
        }

        new_images = [

            {
                "listing_id":
                    listing_id,

                "image_url":
                    image_url
            }

            for image_url in image_urls

            if image_url not in existing_urls
        ]

        if new_images:

            (
                supabase

                .table("listing_images")

                .insert(new_images)

                .execute()
            )

            print(
                f"{len(new_images)} imagens adicionadas"
            )

    @staticmethod
    def upsert_listing(
        payload: dict
    ):

        # =====================================
        # IDENTIFICADOR
        # =====================================

        if payload.get("code"):

            existing = (

                supabase

                .table("listings")

                .select("*")

                .match({

                    "provider":
                        payload["provider"],

                    "code":
                        payload["code"]
                })

                .limit(1)

                .execute()
            )

        else:

            existing = (

                supabase

                .table("listings")

                .select("*")

                .eq(
                    "url",
                    payload["url"]
                )

                .limit(1)

                .execute()
            )

        # =====================================
        # UPDATE
        # =====================================

        if existing.data:

            listing = (
                existing.data[0]
            )

            old_price = ListingsService.normalize_price(
                listing.get(
                    "current_price"
                )
            )

            new_price = ListingsService.normalize_price(
                payload.get(
                    "current_price"
                )
            )

            print(
                f"Listing id={listing['id']} - "
                f"old_price={old_price}({type(old_price).__name__}) "
                f"new_price={new_price}({type(new_price).__name__})"
            )

            response = (

                supabase

                .table("listings")

                .update({

                    "provider":
                        payload[
                            "provider"
                        ],

                    "code":
                        payload.get(
                            "code"
                        ),

                    "title":
                        payload[
                            "title"
                        ],

                    "neighborhood":
                        payload[
                            "neighborhood"
                        ],

                    "bedrooms":
                        payload[
                            "bedrooms"
                        ],

                    "bathrooms":
                        payload[
                            "bathrooms"
                        ],

                    "area":
                        payload[
                            "area"
                        ],

                    "url":
                        payload[
                            "url"
                        ],

                    "thumbnail_url":
                        payload[
                            "thumbnail_url"
                        ],

                    "current_price":
                        new_price,

                    "price_label":
                        payload[
                            "price_label"
                        ],
                })

                .eq(
                    "id",
                    listing["id"]
                )

                .execute()
            )

            # =================================
            # PRICE CHANGED
            # =================================

            if old_price != new_price:

                # =============================
                # HISTORY
                # =============================

                (
                    supabase

                    .table(
                        "listing_price_history"
                    )

                    .insert({

                        "listing_id":
                            listing["id"],

                        "price":
                            int(new_price)
                    })

                    .execute()
                )

                # =============================
                # EVENT TYPE
                # =============================

                event_type = (

                    "price_drop"

                    if new_price < old_price

                    else "price_up"
                )

                # =============================
                # EVENT TITLE
                # =============================

                event_title = (

                    "Preço reduzido"

                    if new_price < old_price

                    else "Preço aumentado"
                )

                # =============================
                # EVENT
                # =============================

                (
                    supabase

                    .table(
                        "listing_events"
                    )

                    .insert({

                        "listing_id":
                            listing["id"],

                        "type":
                            event_type,

                        "title":
                            event_title,

                        "description":
                            payload["title"],

                        "old_price":
                            int(old_price),

                        "new_price":
                            int(new_price)
                    })

                    .execute()
                )

                print(
                    "PRICE UPDATED"
                )

            # =================================
            # IMAGES
            # =================================

            ListingsService.sync_images(

                listing["id"],

                payload.get(
                    "image_urls",
                    []
                )
            )

            print(
                "LISTING UPDATED"
            )

            return response.data

        # =====================================
        # INSERT
        # =====================================

        response = (

            supabase

            .table("listings")

            .insert({

                "provider":
                    payload[
                        "provider"
                    ],

                "code":
                    payload.get(
                        "code"
                    ),

                "title":
                    payload[
                        "title"
                    ],

                "neighborhood":
                    payload[
                        "neighborhood"
                    ],

                "bedrooms":
                    payload[
                        "bedrooms"
                    ],

                "bathrooms":
                    payload[
                        "bathrooms"
                    ],

                "area":
                    payload[
                        "area"
                    ],

                "url":
                    payload[
                        "url"
                    ],

                "thumbnail_url":
                    payload[
                        "thumbnail_url"
                    ],

                "current_price":
                    ListingsService.normalize_price(
                        payload[
                            "current_price"
                        ]
                    ),

                "price_label":
                    payload[
                        "price_label"
                    ],
            })

            .execute()
        )

        created_listing = (
            response.data[0]
        )

        # =====================================
        # INITIAL HISTORY
        # =====================================

        (
            supabase

            .table(
                "listing_price_history"
            )

            .insert({

                "listing_id":
                    created_listing["id"],

                "price":
                    ListingsService.normalize_price(
                        payload[
                            "current_price"
                        ]
                    )
            })

            .execute()
        )

        # =====================================
        # INITIAL EVENT
        # =====================================

        (
            supabase

            .table("listing_events")

            .insert({

                "listing_id":
                    created_listing["id"],

                "type":
                    "created",

                "title":
                    "Imóvel adicionado",

                "description":
                    payload["title"]
            })

            .execute()
        )

        # =====================================
        # IMAGES
        # =====================================

        ListingsService.sync_images(

            created_listing["id"],

            payload.get(
                "image_urls",
                []
            )
        )

        print(
            "LISTING CREATED"
        )

        return response.data

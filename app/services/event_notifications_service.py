from app.config.supabase import (
    supabase
)


class EventNotificationsService:

    @staticmethod
    def get_pending_events():

        response = (

            supabase

            .table("listing_events")

            .select("*")

            .eq(
                "notified",
                False
            )

            .execute()
        )

        return response.data

    @staticmethod
    def mark_as_notified(
        event_id: int
    ):

        (
            supabase

            .table("listing_events")

            .update({
                "notified": True
            })

            .eq("id", event_id)

            .execute()
        )
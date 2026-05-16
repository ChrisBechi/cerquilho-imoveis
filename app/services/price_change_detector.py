class PriceChangeDetector:

    @staticmethod
    def has_price_changed(
        old_price_numeric,
        new_price_numeric
    ):

        return (
            old_price_numeric
            != new_price_numeric
        )

    @staticmethod
    def is_price_lower(
        old_price_numeric,
        new_price_numeric
    ):

        return (
            new_price_numeric
            < old_price_numeric
        )
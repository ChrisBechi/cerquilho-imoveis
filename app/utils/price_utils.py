import re


def extract_price_value(
    price
) -> int:

    if not price:
        return 0

    if isinstance(
        price,
        int
    ):
        return price * 100

    if isinstance(
        price,
        float
    ):
        return int(
            round(
                price * 100
            )
        )

    price = str(price)

    match = re.search(
         r"(?:R\$\s*)?([\d.]+(?:,\d{2})?)",
        price
    )

    if not match:
        return 0

    value = match.group(1)

    if (
        "," not in value
        and "." in value
        and len(value.rsplit(".", 1)[1]) == 2
    ):
        try:
            return int(
                round(
                    float(value) * 100
                )
            )
        except ValueError:
            return 0

    value = (
        value
        .replace(".", "")
        .replace(",", ".")
    )

    try:

        # float temporário apenas
        # para conversão

        numeric_value = float(value)

        # converte para centavos

        return int(
            round(
                numeric_value * 100
            )
        )

    except ValueError:

        return 0

def format_price(
    value: int
):

    return (

        f"R$ {(value / 100):,.2f}"

        .replace(",", "X")

        .replace(".", ",")

        .replace("X", ".")
    )

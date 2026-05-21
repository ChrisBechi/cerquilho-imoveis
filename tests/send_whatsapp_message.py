from app.services.whatsapp.whatsapp_notifier import WhatsAppNotifier

if __name__ == "__main__":

    notifier = WhatsAppNotifier()

    listing = {

        'code': 'L2123',

        "title":
            "Casa moderna com piscina",

        "price_label":
            "R$ 850.000",

        "bedrooms":
            3,

        "bathrooms":
            2,

        "provider":
            "Imobiliária XPTO",

        "url":
            "https://google.com",

        "contact": "11969585712",

        "thumbnail_url":
            "https://images.unsplash.com/photo-1568605114967-8130f3a36994"
    }

    notifier.send_new_listing(
        listing
    )
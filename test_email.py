import smtplib


EMAIL = "christianbechi9@gmail.com"
PASSWORD = "eywpewiuldkkajqz"


try:

    server = smtplib.SMTP(
        "smtp.gmail.com",
        587
    )

    server.starttls()

    server.login(
        EMAIL,
        PASSWORD
    )

    print("LOGIN OK")

    server.quit()

except Exception as error:

    print(error)
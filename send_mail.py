import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

TO = "filipczuk.kuba@gmail.com"
FROM = "filipczuk.kuba@gmail.com"
SUBJECT = "One Design — zaktualizowany dashboard (persony + trendy + ceny)"

FILES = [
    r"C:\Users\filip\Desktop\claudecode\onedesign_personas.html",
]

if len(sys.argv) < 2:
    print("Użycie: python send_mail.py HASLO_APLIKACJI")
    print("Jak uzyskać hasło: myaccount.google.com → Bezpieczeństwo → Hasła do aplikacji")
    sys.exit(1)

app_password = sys.argv[1].replace(" ", "")

msg = MIMEMultipart()
msg["From"] = FROM
msg["To"] = TO
msg["Subject"] = SUBJECT

body = """Cześć,

W załączniku zaktualizowany dashboard One Design z nowymi funkcjami:

• Selektor liczby dzieci (0 / 1 / 2 / 3 / 4+) w każdej personie
• Dochód per osoba vs. per para (dane GUS 2025)
• Koszty per m² dynamicznie wyliczane (remont + projekt)
• Nowa sekcja: Rynek Polski — ceny mieszkań, remont, fee projektanta
• 10 kart trendów globalnych: Japandi, Wabi-Sabi, Organic Luxe, Quiet Luxury,
  Maximalism, Scanditalia, Biophilic, Mediterranean, Smart Home, Warszawa

Plik otwórz w przeglądarce — działa offline, bez serwera.

One Design — Claude Code
"""

msg.attach(MIMEText(body, "plain", "utf-8"))

for filepath in FILES:
    with open(filepath, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(filepath)}")
    msg.attach(part)

print(f"Łączenie z Gmail SMTP...")
with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(FROM, app_password)
    server.sendmail(FROM, TO, msg.as_string())

print(f"✓ Wysłano do {TO}")

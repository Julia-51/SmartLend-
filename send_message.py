import smtplib
from email.message import EmailMessage

msg = EmailMessage()
msg["From"] = "smartlend@outlook.fr"
msg["To"] = "ton_adresse_test@gmail.com"
msg["Subject"] = "Test SmartLend"
msg.set_content("Bonjour, ceci est un test d'envoi d'email via Outlook SMTP.")

with smtplib.SMTP("smtp.office365.com", 587) as s:
    s.starttls()
    s.login("smartlend@outlook.fr", "gvjldnjkwrsombbw")
    s.send_message(msg)

import smtplib
import os
from email.mime.text import MIMEText

def send_invite_email(to_email, first_name, invite_link):
    msg = MIMEText(
        f"Hi {first_name},\n\n"
        f"An admin has added you to TASKTRAC. Click the link below to set your password:\n\n"
        f"{invite_link}\n\n"
        f"This link expires in 7 days."
    )
    msg["Subject"] = "Set your TASKTRAC password"
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = to_email

    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"])) as server:
        server.starttls()
        server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        server.sendmail(os.environ["SMTP_USER"], [to_email], msg.as_string())
        
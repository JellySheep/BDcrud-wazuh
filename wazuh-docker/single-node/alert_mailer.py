import time
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

ALERT_FILE = "/var/ossec/logs/alerts/alerts.log"
SMTP_HOST = "wazuh-postfix"
SMTP_PORT = 25

MAIL_FROM = "MAIL"
MAIL_TO = ["PASSWORD"]

CHECK_INTERVAL = 2  # seconds


def send_email(subject, body):
    msg = MIMEText(body, _charset="utf-8")
    msg["From"] = MAIL_FROM
    msg["To"] = ", ".join(MAIL_TO)
    msg["Subject"] = subject

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
        s.sendmail(MAIL_FROM, MAIL_TO, msg.as_string())


def follow(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        f.seek(0, 2)  # jump to EOF
        while True:
            line = f.readline()
            if not line:
                time.sleep(CHECK_INTERVAL)
                continue
            yield line.strip()


def main():
    print("📡 Wazuh alert watcher started")
    alert_path = Path(ALERT_FILE)

    if not alert_path.exists():
        print(f"❌ File not found: {ALERT_FILE}")
        return

    for line in follow(ALERT_FILE):
        if not line:
            continue

        subject = "🚨 Wazuh alert"
        body = line

        try:
            send_email(subject, body)
            print("✉️ Alert email sent")
        except Exception as e:
            print("❌ Email error:", e)


if __name__ == "__main__":
    main()

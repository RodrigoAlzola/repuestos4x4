import requests
import json
import logging
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class BrevoEmailBackend(BaseEmailBackend):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from django.conf import settings
        self.api_key = getattr(settings, 'BREVO_API_KEY', '')

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            try:
                payload = {
                    "sender": {"email": message.from_email.split('<')[-1].rstrip('>').strip(),
                               "name": message.from_email.split('<')[0].strip() or message.from_email},
                    "to": [{"email": to} for to in message.to],
                    "subject": message.subject,
                    "textContent": message.body,
                }

                # Check for HTML content
                if hasattr(message, 'alternatives'):
                    for content, mimetype in message.alternatives:
                        if mimetype == 'text/html':
                            payload["htmlContent"] = content
                            break

                response = requests.post(
                    "https://api.brevo.com/v3/smtp/email",
                    headers={
                        "accept": "application/json",
                        "api-key": self.api_key,
                        "content-type": "application/json",
                    },
                    data=json.dumps(payload),
                )

                if response.status_code == 201:
                    sent += 1
                else:
                    logger.error(f"Brevo API error: {response.status_code} - {response.text}")
                    if not self.fail_silently:
                        raise Exception(f"Brevo API error: {response.text}")

            except Exception as e:
                logger.error(f"Error sending email via Brevo API: {e}")
                if not self.fail_silently:
                    raise
        return sent
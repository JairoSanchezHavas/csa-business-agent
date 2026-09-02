import httpx
from app.config import logger

class WhatsAppClient:
    BASE_URL = "https://graph.facebook.com/v21.0"

    def __init__(self, phone_number_id: str, access_token: str):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def send_text_message(self, to_phone: str, text_body: str) -> dict:
        endpoint = f"{self.BASE_URL}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone.strip().replace("+", ""),
            "type": "text",
            "text": {
                "preview_url": False,
                "body": text_body
            }
        }

        logger.info(f"Enviando mensaje a {to_phone}...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(endpoint, json=payload, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"Error Graph API ({response.status_code}): {response.text}")
                response.raise_for_status()
            data = response.json()
            logger.info(f"Mensaje enviado con exito: {data}")
            return data

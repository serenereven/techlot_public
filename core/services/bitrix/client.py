import requests
from django.conf import settings
from .exceptions import BitrixRequestError, BitrixResponseError


class BitrixClient:
    def __init__(self):
        self.base_url = settings.BITRIX_WEBHOOK_URL
        self.timeout = int(getattr(settings, "BITRIX_TIMEOUT", 5))

    def call(self, method: str, payload: dict) -> dict:
        url = f"{self.base_url}{method}.json"

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            raise BitrixRequestError(str(e)) from e

        data = response.json()

        if "error" in data:
            raise BitrixResponseError(data["error_description"])

        return data

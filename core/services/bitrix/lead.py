from .client import BitrixClient
from django.conf import settings

class BitrixLeadService:

    def __init__(self, client=None):
        self.client = client or BitrixClient()

    def create_from_purchase_request(self, request_obj):
        payload = {
            "fields": {
                "TITLE": request_obj.name, #self._build_title(request_obj),
                "NAME": request_obj.name,
                "PHONE": [
                    {"VALUE": request_obj.phone, "VALUE_TYPE": "WORK"}
                ],
                "OPPORTUNITY": float(request_obj.vehicle.price_rub) if request_obj.vehicle else None,
                "COMMENTS": self._build_comments(request_obj),
                "SOURCE_ID": "WEB",
                "ASSIGNED_BY_ID": settings.BITRIX_ASSIGNED_ID,
            }
        }

        return self.client.call("crm.lead.add", payload)

    def _build_title(self, obj):
        vehicle_title = obj.vehicle.title if obj.vehicle else "Без указания техники"
        vehicle_vin = obj.vehicle.vin if obj.vehicle else "Без VIN"
        
        return f"{obj.get_request_type_display()} - {vehicle_title} - {vehicle_vin}"

    def _build_comments(self, obj):
        vehicle_title = obj.vehicle.title if obj.vehicle else "Не указано"
        vehicle_vin = obj.vehicle.vin if obj.vehicle else "Без VIN"

        return (
            f"Тип заявки: {obj.get_request_type_display()}\n"
            f"Техника: {vehicle_title}\n"
            f"ИНН: {obj.inn or '-'}\n"
            f"VIN: {vehicle_vin or '-'}"
        )
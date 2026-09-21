from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/app", tags=["app"])


@router.get("/version")
def app_version():
    return {
        "version_name": "1.1.5",
        "version_code": 9,
        "apk_url": "https://github.com/artyom129/SlotBridge/releases/download/v1.1.5/SlotBridge-1.1.5-9-production.apk",
        "required": False,
        "changelog": {
            "ru": [
                "Исправлено нажатие карточек услуг, сотрудников, слотов, записей и маршрутов в SlotBridge AI",
                "Добавлено безопасное продолжение AI flow после выбора карточки",
                "Маршрут из нескольких услуг теперь требует явного подтверждения перед атомарной записью",
            ],
            "en": [
                "Fixed taps on service, employee, slot, appointment, and journey cards in SlotBridge AI",
                "Added safe AI flow continuation after selecting a card",
                "Multi-service journeys now require explicit confirmation before atomic booking",
            ],
        },
        "sha256": "6b51c915ceb4ba556503a2654c66c0374390bd419a315aa52784f2f4a706601e",
    }

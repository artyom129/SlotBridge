from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/app", tags=["app"])


@router.get("/version")
def app_version():
    return {
        "version_name": "1.1.6",
        "version_code": 10,
        "apk_url": "https://github.com/artyom129/SlotBridge/releases/download/v1.1.6/SlotBridge-1.1.6-10-production.apk",
        "required": False,
        "changelog": {
            "ru": [
                "Отзывы после завершённых записей",
                "Рейтинги сотрудников и фильтры отзывов",
                "Модерация отзывов, жалобы и официальные ответы",
                "Аналитика отзывов и безопасные AI-сводки",
                "Переход к внешнему отзыву в 2GIS",
            ],
            "en": [
                "Reviews after completed appointments",
                "Employee ratings and review filters",
                "Review moderation, reports, and official replies",
                "Review analytics and privacy-safe AI summaries",
                "External 2GIS review flow",
            ],
        },
        "sha256": "5f5edded8960ad907fcbc5c073b562c2ee44d6974af531462a8355752a7b327d",
    }

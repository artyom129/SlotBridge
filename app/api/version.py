from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/app", tags=["app"])

@router.get("/version")
def app_version():
    return {"version_name": "1.1.1", "version_code": 5, "apk_url": "https://github.com/artyom129/SlotBridge/releases/download/v1.1.1/SlotBridge-1.1.1-5-production.apk", "required": False, "changelog": {"ru": ["Исправлена стабильность и интерфейс SlotBridge AI", "Предотвращены повторные нажатия при сетевых запросах", "Улучшено отображение на небольших экранах и в тёмной теме"], "en": ["Improved SlotBridge AI stability and interface", "Prevented repeated actions during network requests", "Improved small-screen and dark-theme layouts"]}, "sha256": "e02a38b2524156791a2e31b4a9f6748374a1d7b71a30d18a6e3d387d3b551bfd"}

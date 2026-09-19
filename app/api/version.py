from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/app", tags=["app"])

@router.get("/version")
def app_version():
    return {"version_name": "1.1.0", "version_code": 4, "apk_url": "https://github.com/artyom129/SlotBridge/releases/download/v1.1.0/SlotBridge-1.1.0-4-production.apk", "required": False, "changelog": {"ru": ["Умные рекомендации времени", "Помощь при конфликте записи", "Профиль, SlotBridge AI и обновления"], "en": ["Smart time recommendations", "Booking conflict rescue", "Profile, SlotBridge AI, and updates"]}, "sha256": "acd8252bb425d053f879360f6d08d5a12f7139405373dd16a721ac737c7a3e9d"}

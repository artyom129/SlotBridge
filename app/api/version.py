from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/app", tags=["app"])

@router.get("/version")
def app_version():
    return {"version_name": "1.1.2", "version_code": 6, "apk_url": "https://github.com/artyom129/SlotBridge/releases/download/v1.1.2/SlotBridge-1.1.2-6-production.apk", "required": False, "changelog": {"ru": ["Исправлено нажатие быстрых действий SlotBridge AI", "Улучшены загрузка, повтор запроса и обработка временной недоступности AI", "Исправлена форма редактирования профиля"], "en": ["Fixed SlotBridge AI quick-action taps", "Improved loading, retry, and temporary AI outage handling", "Fixed the edit-profile form"]}, "sha256": "8a12508ad5f08f23189dc73175e810ce5caaed5b75a813fbabbb07f1761c1c2f"}

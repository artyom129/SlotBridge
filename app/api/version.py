from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/app", tags=["app"])

@router.get("/version")
def app_version():
    return {"version_name": "1.1.4", "version_code": 8, "apk_url": "https://github.com/artyom129/SlotBridge/releases/download/v1.1.4/SlotBridge-1.1.4-8-production.apk", "required": False, "changelog": {"ru": ["Добавлен Multi-Service Smart Journey для записи на несколько услуг за один визит", "Добавлены стратегии: быстрее всего, раньше всего и меньше специалистов", "Атомарное бронирование отменяет весь маршрут при конфликте"], "en": ["Added Multi-Service Smart Journey for booking several services in one visit", "Added fastest, earliest, and fewest-employees strategies", "Atomic booking rolls back the whole journey on conflict"]}, "sha256": "dbe65405ccbed960e95ad7400c36e44cc908f3579f630ea4a7039928b6176d0d"}

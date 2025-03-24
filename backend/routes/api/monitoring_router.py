from fastapi import APIRouter

router = APIRouter()

@router.get("/monitor")
async def monitor_devices():
    return {"status": "monitoring"}
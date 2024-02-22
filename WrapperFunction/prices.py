from fastapi import APIRouter

router = APIRouter()

@router.get("/prices", tags=["Strømpriser"])

async def get_prices():
    # Implement your logic to fetch or calculate prices here
    return {"message": "Her kommer der strømpriser"}
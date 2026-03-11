from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import BASE_URL
from app.db.session import init_db, get_db
from app.api.routes_users import router as users_router
from app.api.routes_meals import router as meals_router
from app.api.routes_reports import router as reports_router
from app.services.meal_service import analyze_photo


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    # shutdown if needed


app = FastAPI(title="Meal Mentor API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(users_router)
app.include_router(meals_router)
app.include_router(reports_router)


# Legacy: Streamlit (ui.py) calls POST /generate_response
@app.post("/generate_response")
async def generate_response(request: Request):
    """Accept { \"image_base64\": \"...\" }, return ingredients + optional nutrition."""
    try:
        data = await request.json()
        image_base64 = data.get("image_base64")
        if not image_base64:
            raise HTTPException(status_code=400, detail="Base64 image data is required.")
        import base64 as b64
        try:
            b64.b64decode(image_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid Base64: {e}") from e
        return analyze_photo(image_base64)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import MEAL_PHOTOS_DIR
from app.db.session import init_db
from app.interfaces.api.routes_users import router as users_router
from app.interfaces.api.routes_meals import router as meals_router
from app.interfaces.api.routes_reports import router as reports_router
from app.interfaces.api.routes_nutrition import router as nutrition_router
from app.interfaces.api.routes_subscriptions import router as subscriptions_router
from app.routers.auth import router as auth_router
from app.routers.users import router as users_web_router
from app.core.use_cases.meal_analysis import analyze_meal_from_image_base64


@asynccontextmanager
async def lifespan(app: FastAPI):
    MEAL_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    yield
    # shutdown if needed


app = FastAPI(title="Meal Mentor API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(users_router)
app.include_router(meals_router)
app.include_router(reports_router)
app.include_router(nutrition_router)
app.include_router(subscriptions_router)
app.include_router(auth_router)
app.include_router(users_web_router)

app.mount(
    "/media/meals",
    StaticFiles(directory=str(MEAL_PHOTOS_DIR)),
    name="meal_photos",
)


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
        return analyze_meal_from_image_base64(image_base64).to_api_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

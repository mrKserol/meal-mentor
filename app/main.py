from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.infrastructure.storage.additive_photo_storage import get_upload_root as get_additive_upload_root
from app.infrastructure.storage.meal_photo_storage import get_upload_root
from app.db.session import init_db
from app.interfaces.api.routes_users import router as users_router
from app.interfaces.api.routes_meals import router as meals_router
from app.interfaces.api.routes_reports import router as reports_router
from app.interfaces.api.routes_nutrition import router as nutrition_router
from app.interfaces.api.routes_subscriptions import router as subscriptions_router
from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router
from app.routers.consents import router as consents_router
from app.routers.curator import router as curator_router
from app.routers.user_additives import router as user_additives_router
from app.routers.users import router as users_web_router
from app.core.use_cases.meal_analysis import analyze_meal_from_image_base64


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
app.include_router(nutrition_router)
app.include_router(subscriptions_router)
app.include_router(auth_router)
app.include_router(consents_router)
app.include_router(users_web_router)
app.include_router(user_additives_router)
app.include_router(admin_router)
app.include_router(curator_router)

# StaticFiles checks the path at import time — before lifespan runs.
_meal_photo_root = get_upload_root()
_meal_photo_root.mkdir(parents=True, exist_ok=True)
app.mount(
    "/media/meal_photos",
    StaticFiles(directory=str(_meal_photo_root)),
    name="meal_photos_media",
)

_additive_photo_root = get_additive_upload_root()
_additive_photo_root.mkdir(parents=True, exist_ok=True)
app.mount(
    "/media/additives",
    StaticFiles(directory=str(_additive_photo_root)),
    name="additives_media",
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

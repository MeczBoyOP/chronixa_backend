from fastapi import APIRouter

from app.api.v1 import auth

# The v1 surface. Mounted in `app.main` under settings.API_V1_PREFIX.
api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

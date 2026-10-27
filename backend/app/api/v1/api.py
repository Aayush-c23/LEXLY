"""
API v1 Router Configuration.
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import analyze, session

api_router = APIRouter()
api_router.include_router(analyze.router, tags=["Intake & Analysis"])
api_router.include_router(session.router, tags=["Interactive Clarification"])


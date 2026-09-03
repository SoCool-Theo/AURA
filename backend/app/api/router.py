from fastapi import APIRouter

from app.api.routes.agent import router as agent_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.portfolio import router as portfolio_router
from app.api.routes.reporting import router as reporting_router
from app.api.routes.simulation import router as simulation_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(agent_router)
api_router.include_router(portfolio_router)
api_router.include_router(reporting_router)
api_router.include_router(simulation_router)

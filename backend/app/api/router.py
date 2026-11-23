from fastapi import APIRouter

from app.api.v1 import auth, crm, system, users

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(crm.dashboard)
api_router.include_router(crm.agents)
api_router.include_router(crm.customers)
api_router.include_router(crm.enquiries)

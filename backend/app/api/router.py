from fastapi import APIRouter

from app.api.v1 import admin_tools, ai, auth, crm, inventory, itineraries, media, pricing, proposals, system, users

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(crm.dashboard)
api_router.include_router(crm.agents)
api_router.include_router(crm.customers)
api_router.include_router(crm.enquiries)
api_router.include_router(inventory.router)
api_router.include_router(media.router)
api_router.include_router(itineraries.router)
api_router.include_router(proposals.router)
api_router.include_router(pricing.router)
api_router.include_router(ai.router)
api_router.include_router(admin_tools.router)

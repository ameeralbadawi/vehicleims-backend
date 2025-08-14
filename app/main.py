from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import car
from app.routers import watchlists
from app.routers import clerk_webhook


app = FastAPI()

# CORS: Allow frontend domain to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://jolly-sand-0ed3a040f.2.azurestaticapps.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(car.router)
app.include_router(watchlists.router)
app.include_router(clerk_webhook.router)


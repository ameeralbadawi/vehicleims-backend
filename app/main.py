from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.routers import car, watchlists, clerk_webhook
from app.auth import get_authenticated_user  # <-- new

app = FastAPI()

# CORS: Allow frontend domain to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://jolly-sand-0ed3a040f.2.azurestaticapps.net"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(car.router, dependencies=[Depends(get_authenticated_user)])   # protect routes
app.include_router(watchlists.router, dependencies=[Depends(get_authenticated_user)])
app.include_router(clerk_webhook.router)  # webhook doesn’t need session auth

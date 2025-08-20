from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.routers import car, watchlists, clerk_webhook
from app.auth import get_authenticated_user

app = FastAPI()

# CORS: Allow frontend domain to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://jolly-sand-0ed3a040f.2.azurestaticapps.net",
        "https://vehicleims-backend-a9ffehefgdhuahc0.centralus-01.azurewebsites.net"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # ADD THIS - important for CORS
    max_age=600,  # ADD THIS - cache preflight requests for 10 minutes
)

# Register routers
# REMOVE dependencies from include_router - handle auth in individual endpoints instead
app.include_router(car.router)
app.include_router(watchlists.router)
app.include_router(clerk_webhook.router)  # webhook doesn't need session auth

# Add a health check endpoint (important for Azure)
@app.get("/")
async def root():
    return {"status": "healthy", "message": "Vehicle Inventory Management System API"}

# Add a test endpoint for authentication debugging
@app.get("/test-auth")
async def test_auth(user_id: str = Depends(get_authenticated_user)):
    return {"status": "success", "user_id": user_id, "message": "Authentication is working!"}
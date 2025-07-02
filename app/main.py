from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import car

app = FastAPI()

# 👇 Add CORS middleware before including routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your router
app.include_router(car.router)


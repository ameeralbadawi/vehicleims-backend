from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import car  # adjust path if needed

app = FastAPI()

# Allow your frontend URL for CORS
origins = [
    "https://jolly-sand-0ed3a040f.2.azurestaticapps.net"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # allow only your frontend domain
    allow_credentials=True,
    allow_methods=["*"],    # allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],    # allow all headers
)

app.include_router(car.router)

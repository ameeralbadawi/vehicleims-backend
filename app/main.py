from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from app.routers import car

app = FastAPI()

# Force all requests to HTTPS
app.add_middleware(HTTPSRedirectMiddleware)

# Allow frontend domain to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jolly-sand-0ed3a040f.2.azurestaticapps.net"  # Your deployed static web app URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register your routers
app.include_router(car.router)

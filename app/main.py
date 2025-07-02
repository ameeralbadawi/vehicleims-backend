from fastapi import FastAPI
from app.routers import car

app = FastAPI()
app.include_router(car.router)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Car
from app.schemas import CarCreate

router = APIRouter()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/cars/")
def create_car(car: CarCreate, db: Session = Depends(get_db)):
    existing = db.query(Car).filter(Car.vin == car.vin).first()
    if existing:
        raise HTTPException(status_code=400, detail="Car with this VIN already exists.")
    
    # Ensure status is inside the nested data, default to 'Available' if missing
    car_data = dict(car.data)  # make a copy
    if "status" not in car_data:
        car_data["status"] = "Available"
    
    new_car = Car(vin=car.vin, data=car_data)
    db.add(new_car)
    db.commit()
    db.refresh(new_car)
    return new_car


@router.get("/cars/")
def get_all_cars(db: Session = Depends(get_db)):
    return db.query(Car).all()

@router.delete("/cars/{vin}")
def delete_car(vin: str, db: Session = Depends(get_db)):
    car = db.query(Car).filter(Car.vin == vin).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found.")
    db.delete(car)
    db.commit()
    return {"detail": f"Car with VIN {vin} deleted."}

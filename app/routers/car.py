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
    cars = db.query(Car).all()
    result = []

    for car in cars:
        try:
            data = car.data or {}
            car_details = {
                "vin": car.vin,
                "status": data.get("status", "Unknown"),
                **(data.get("CarDetails") or {}),
                **(data.get("EstimateDetails") or {}),
                **(data.get("PurchaseDetails") or {}),
                **(data.get("TransportDetails") or {}),
                **(data.get("PartsDetails") or {}),
                **(data.get("MechanicDetails") or {}),
                **(data.get("BodyshopDetails") or {}),
                **(data.get("MiscellaniousDetails") or {}),
                **(data.get("saleDetails") or {}),
            }
            result.append(car_details)
        except Exception as e:
            print(f"Error processing car {car.vin}: {e}")
            continue  # skip broken entry
    return result

@router.delete("/cars/{vin}")
def delete_car(vin: str, db: Session = Depends(get_db)):
    car = db.query(Car).filter(Car.vin == vin).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found.")
    db.delete(car)
    db.commit()
    return {"detail": f"Car with VIN {vin} deleted."}

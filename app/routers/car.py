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
    car_data = dict(car.data)
    if "status" not in car_data:
        car_data["status"] = "Available"
    
    new_car = Car(vin=car.vin, data=car_data)
    db.add(new_car)
    db.commit()
    db.refresh(new_car)

    # Return a flat structure like GET does
    nested = car_data.get("Car", {})
    return {
        "vin": new_car.vin,
        "status": car_data.get("status", "Unknown"),
        **(nested.get("CarDetails") or {}),
        **(nested.get("EstimateDetails") or {}),
        **(nested.get("PurchaseDetails") or {}),
        **(nested.get("TransportDetails") or {}),
        **(nested.get("PartsDetails") or {}),
        **(nested.get("MechanicDetails") or {}),
        **(nested.get("BodyshopDetails") or {}),
        **(nested.get("MiscellaniousDetails") or {}),
        **(nested.get("saleDetails") or {}),
        "id": new_car.id,
    }

@router.get("/cars/")
def get_all_cars(db: Session = Depends(get_db)):
    cars = db.query(Car).all()
    result = []

    for car in cars:
        try:
            data = car.data or {}
            status = data.get("status", "Unknown")
            nested = data.get("Car", {})  # FIX: drill into "Car" key

            car_info = {
                "id": car.id,
                "vin": car.vin,
                "status": status,
                **(nested.get("CarDetails") or {}),
                **(nested.get("EstimateDetails") or {}),
                **(nested.get("PurchaseDetails") or {}),
                **(nested.get("TransportDetails") or {}),
                **(nested.get("PartsDetails") or {}),
                **(nested.get("MechanicDetails") or {}),
                **(nested.get("BodyshopDetails") or {}),
                **(nested.get("MiscellaniousDetails") or {}),
                **(nested.get("saleDetails") or {}),
            }

            result.append(car_info)

        except Exception as e:
            print(f"Error processing car {car.vin}: {e}")
            continue  # skip bad records
    return result

@router.delete("/cars/{vin}")
def delete_car(vin: str, db: Session = Depends(get_db)):
    car = db.query(Car).filter(Car.vin == vin).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found.")
    db.delete(car)
    db.commit()
    return {"detail": f"Car with VIN {vin} deleted."}

@router.patch("/cars/{vin}")
def update_car_status(vin: str, payload: dict, db: Session = Depends(get_db)):
    new_status = payload.get("status")

    if not new_status:
        raise HTTPException(status_code=400, detail="Missing 'status' in payload")

    car = db.query(Car).filter(Car.vin == vin).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    # Make sure the nested data dict exists
    if car.data is None:
        car.data = {}

    # Update both nested and optional top-level status
    car.data["status"] = new_status
    car.status = new_status  # optional but useful for querying

    db.commit()
    db.refresh(car)

    return {
        "vin": vin,
        "status": new_status,
        "id": car.id  # <- include this!
    }


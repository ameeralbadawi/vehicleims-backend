# routers/car.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.database import SessionLocal
from app.models import Car
from app.schemas import CarCreate
from app.auth import get_authenticated_user

router = APIRouter()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CREATE CAR
@router.post("/cars/")
async def create_car(
    car: CarCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_authenticated_user)
):
    existing = db.query(Car).filter(Car.vin == car.vin, Car.user_id == user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Car with this VIN already exists.")

    car_data = dict(car.data)
    if "status" not in car_data:
        car_data["status"] = "Available"

    new_car = Car(vin=car.vin, data=car_data, user_id=user_id)
    db.add(new_car)
    db.commit()
    db.refresh(new_car)

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

# GET ALL CARS
@router.get("/cars/")
async def get_all_cars(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_authenticated_user)
):
    cars = db.query(Car).filter(Car.user_id == user_id).all()
    result = []

    for car in cars:
        try:
            data = car.data or {}
            status = data.get("status", "Unknown")
            nested = data.get("Car", {})

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
            continue
    return result

# DELETE CAR
@router.delete("/cars/{vin}")
async def delete_car(
    vin: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_authenticated_user)
):
    car = db.query(Car).filter(Car.vin == vin, Car.user_id == user_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found.")
    db.delete(car)
    db.commit()
    return {"detail": f"Car with VIN {vin} deleted."}

# UPDATE CAR STATUS
@router.patch("/cars/{vin}")
async def update_car_status(
    vin: str,
    payload: dict,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_authenticated_user)
):
    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Missing 'status' in payload")

    car = db.query(Car).filter(Car.vin == vin, Car.user_id == user_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    if car.data is None:
        car.data = {}

    car.data["status"] = new_status
    flag_modified(car, "data")
    db.commit()
    return {"vin": vin, "status": new_status, "id": car.id}

# FULL UPDATE CAR
@router.put("/cars/{vin}")
async def update_car(
    vin: str,
    payload: dict,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_authenticated_user)
):
    car = db.query(Car).filter(Car.vin == vin, Car.user_id == user_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found.")

    if car.data is None:
        car.data = {}

    incoming_car_data = payload.get("data", {})
    car.data["Car"] = incoming_car_data
    car.data["status"] = payload.get("status", car.data.get("status", "Available"))
    flag_modified(car, "data")
    db.commit()
    db.refresh(car)

    nested = car.data.get("Car", {})
    return {
        "vin": car.vin,
        "status": car.data.get("status", "Unknown"),
        **(nested.get("CarDetails") or {}),
        **(nested.get("EstimateDetails") or {}),
        **(nested.get("PurchaseDetails") or {}),
        **(nested.get("TransportDetails") or {}),
        **(nested.get("PartsDetails") or {}),
        **(nested.get("MechanicDetails") or {}),
        **(nested.get("BodyshopDetails") or {}),
        **(nested.get("MiscellaniousDetails") or {}),
        **(nested.get("saleDetails") or {}),
        **(nested.get("InvoiceDetails") or {}),
        "id": car.id,
    }

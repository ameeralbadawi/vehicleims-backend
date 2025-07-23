from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import crud, schemas
from app.dependencies import get_db

router = APIRouter(
    prefix="/watchlists",
    tags=["watchlists"]
)

# Get all watchlists
@router.get("/", response_model=List[schemas.WatchlistRead])
def read_watchlists(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    watchlists = crud.get_watchlists(db, skip=skip, limit=limit)
    return watchlists

# Create a new watchlist
@router.post("/", response_model=schemas.WatchlistRead)
def create_watchlist(watchlist: schemas.WatchlistCreate, db: Session = Depends(get_db)):
    return crud.create_watchlist(db, watchlist)

# Get a watchlist by ID
@router.get("/{watchlist_id}", response_model=schemas.WatchlistRead)
def read_watchlist(watchlist_id: int, db: Session = Depends(get_db)):
    db_watchlist = crud.get_watchlist(db, watchlist_id)
    if db_watchlist is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return db_watchlist


# Add a car to the watchlist
@router.post("/{watchlist_id}/cars/", response_model=schemas.WatchlistItemRead)
def add_car_to_watchlist(watchlist_id: int, car: schemas.WatchlistCarCreate, db: Session = Depends(get_db)):
    # Create the watchlist car entry first
    db_car = crud.create_watchlist_car(db, car)
    # Create the watchlist item linking car to watchlist
    watchlist_item_in = schemas.WatchlistItemCreate(watchlist_id=watchlist_id, car_id=db_car.id)
    db_item = crud.create_watchlist_item(db, watchlist_item_in)
    return db_item

# Get all cars in a watchlist
@router.get("/{watchlist_id}/cars/", response_model=List[schemas.WatchlistItemRead])
def get_cars_in_watchlist(watchlist_id: int, db: Session = Depends(get_db)):
    items = crud.get_watchlist_items_by_watchlist(db, watchlist_id)
    return items

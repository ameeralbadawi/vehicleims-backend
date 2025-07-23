from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class CarCreate(BaseModel):
    vin: str
    data: Dict[str, Any]  # Accepts full nested JSON

# WatchlistCar schemas
class WatchlistCarBase(BaseModel):
    vin: Optional[str] = None
    details: Optional[dict] = None  # flexible JSON

class WatchlistCarCreate(WatchlistCarBase):
    pass

class WatchlistCarRead(WatchlistCarBase):
    id: int

    class Config:
        orm_mode = True


# WatchlistItem schemas
class WatchlistItemBase(BaseModel):
    watchlist_id: int
    car_id: int

class WatchlistItemCreate(WatchlistItemBase):
    pass

class WatchlistItemRead(WatchlistItemBase):
    id: int
    car: WatchlistCarRead

    class Config:
        orm_mode = True


# Watchlist schemas
class WatchlistBase(BaseModel):
    name: str

class WatchlistCreate(WatchlistBase):
    pass

class WatchlistRead(WatchlistBase):
    id: int
    items: List[WatchlistItemRead] = []

    class Config:
        orm_mode = True

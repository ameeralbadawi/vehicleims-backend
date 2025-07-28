from sqlalchemy.orm import Session
from app import models, schemas

# Watchlist CRUD
def get_watchlist(db: Session, watchlist_id: int):
    return db.query(models.Watchlist).filter(models.Watchlist.id == watchlist_id).first()

def get_watchlists(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Watchlist).offset(skip).limit(limit).all()

def create_watchlist(db: Session, watchlist: schemas.WatchlistCreate):
    db_watchlist = models.Watchlist(name=watchlist.name)
    db.add(db_watchlist)
    db.commit()
    db.refresh(db_watchlist)
    return db_watchlist

def update_watchlist_name(db: Session, watchlist_id: int, new_name: str):
    watchlist = db.query(models.Watchlist).filter(models.Watchlist.id == watchlist_id).first()
    if not watchlist:
        return None
    watchlist.name = new_name
    db.commit()
    db.refresh(watchlist)
    return watchlist

def delete_watchlist(db: Session, watchlist_id: int):
    watchlist = db.query(models.Watchlist).filter(models.Watchlist.id == watchlist_id).first()
    if not watchlist:
        return None

    # Delete any related WatchlistItems first if cascade isn't enabled
    db.query(models.WatchlistItem).filter(models.WatchlistItem.watchlist_id == watchlist_id).delete()

    db.delete(watchlist)
    db.commit()
    return watchlist




# WatchlistCar CRUD
def get_watchlist_car(db: Session, car_id: int):
    return db.query(models.WatchlistCar).filter(models.WatchlistCar.id == car_id).first()

def create_watchlist_car(db: Session, car: schemas.WatchlistCarCreate):
    db_car = models.WatchlistCar(vin=car.vin, details=car.details)
    db.add(db_car)
    db.commit()
    db.refresh(db_car)
    return db_car


# WatchlistItem CRUD
def create_watchlist_item(db: Session, item: schemas.WatchlistItemCreate):
    db_item = models.WatchlistItem(watchlist_id=item.watchlist_id, car_id=item.car_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def get_watchlist_items_by_watchlist(db: Session, watchlist_id: int):
    return db.query(models.WatchlistItem).filter(models.WatchlistItem.watchlist_id == watchlist_id).all()

def get_watchlist_item(db: Session, watchlist_id: int, car_id: int):
    return db.query(models.WatchlistItem).filter(
        models.WatchlistItem.watchlist_id == watchlist_id,
        models.WatchlistItem.car_id == car_id
    ).first()


def delete_watchlist_item(db: Session, watchlist_id: int, car_id: int):
    try:
        db_item = db.query(models.WatchlistItem).filter(
            models.WatchlistItem.watchlist_id == watchlist_id,
            models.WatchlistItem.car_id == car_id
        ).first()
        
        if not db_item:
            return False
            
        # Check if car exists in other watchlists before deleting
        car_in_other_watchlists = db.query(models.WatchlistItem).filter(
            models.WatchlistItem.car_id == car_id,
            models.WatchlistItem.watchlist_id != watchlist_id
        ).count() > 0
        
        db.delete(db_item)
        
        # Only delete the car if it's not in any other watchlists
        if not car_in_other_watchlists:
            db_car = db.query(models.WatchlistCar).filter(
                models.WatchlistCar.id == car_id
            ).first()
            if db_car:
                db.delete(db_car)
        
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        raise e

def is_car_in_any_watchlist(db: Session, car_id: int) -> bool:
    return db.query(models.WatchlistItem).filter(
        models.WatchlistItem.car_id == car_id
    ).count() > 0

def delete_watchlist_car(db: Session, car_id: int):
    db_car = db.query(models.WatchlistCar).filter(
        models.WatchlistCar.id == car_id
    ).first()
    if db_car:
        db.delete(db_car)
        db.commit()
        return db_car
    return None

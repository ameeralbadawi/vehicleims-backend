from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Table
from app.database import Base
from sqlalchemy.orm import relationship

class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
    vin = Column(String, unique=True, index=True, nullable=False)
    data = Column(JSON, nullable=False)

class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    # Relationship to items
    items = relationship("WatchlistItem", back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistCar(Base):
    __tablename__ = "watchlist_cars"

    id = Column(Integer, primary_key=True, index=True)
    vin = Column(String, unique=False, index=True, nullable=True)
    details = Column(JSON)  # flexible JSON field to store varied car data

    # Relationship to items
    items = relationship("WatchlistItem", back_populates="car", cascade="all, delete-orphan")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey("watchlists.id"))
    car_id = Column(Integer, ForeignKey("watchlist_cars.id"))

    watchlist = relationship("Watchlist", back_populates="items")
    car = relationship("WatchlistCar", back_populates="items")

from sqlalchemy import Column, Integer, String, JSON
from app.database import Base

class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
    vin = Column(String, unique=True, index=True, nullable=False)
    data = Column(JSON, nullable=False)


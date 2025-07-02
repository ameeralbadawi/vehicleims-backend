from pydantic import BaseModel
from typing import Dict, Any

class CarCreate(BaseModel):
    vin: str
    data: Dict[str, Any]  # Accepts full nested JSON



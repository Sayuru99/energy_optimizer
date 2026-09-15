from pydantic import BaseModel, Field
from datetime import time
from typing import Optional

class MachineCreate(BaseModel):
    name: str
    category: str = "General"
    quantity: int = Field(gt=0)
    power_kw: float = Field(gt=0)
    required_hours: float = Field(gt=0)
    available_start: time
    available_end: time
    priority: str = "Medium"
    color: str = "blue"

class MachineUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[int] = Field(None, gt=0)
    power_kw: Optional[float] = Field(None, gt=0)
    required_hours: Optional[float] = Field(None, gt=0)
    available_start: Optional[time] = None
    available_end: Optional[time] = None
    priority: Optional[str] = None
    color: Optional[str] = None

class MachineOut(BaseModel):
    id: int
    factory_id: int
    name: str
    category: str
    quantity: int
    power_kw: float
    required_hours: float
    available_start: time
    available_end: time
    priority: str
    color: str
    total_power_kw: float = 0

    class Config:
        from_attributes = True
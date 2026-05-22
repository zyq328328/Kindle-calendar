from pydantic import BaseModel
from typing import Literal

class TouchRequest(BaseModel):
    x: int
    y: int
    action: Literal["tap", "release"]

class TouchResponse(BaseModel):
    success: bool
    action: Literal["next_day", "prev_day", "switch_view", "quit", "none", "select_date"] = "none"
    view: str | None = None

class RegionCurrent(BaseModel):
    view: Literal["day", "three_day", "todo", "habit"]
    date: str

class FrameUpdate(BaseModel):
    image_base64: str

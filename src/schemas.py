from typing import List, Any
from pydantic import BaseModel


class HealthOK(BaseModel):
    status: str


class AppHealthOK(BaseModel):
    status: str
    app: str


class Point(BaseModel):
    time: float
    value: float


class PointsList(BaseModel):
    list: List[Point]


class HistoryList(BaseModel):
    list: List[str]


class EmptyResponse(BaseModel):
    pass


class FieldsResponse(BaseModel):
    fields: List[Any]

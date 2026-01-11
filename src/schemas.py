from typing import List, Any, Union
from pydantic import BaseModel
from core.models.test_data import TestMetaData


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
    fields: Union[List[Any], TestMetaData]


class MessageResponse(BaseModel):
    message: str

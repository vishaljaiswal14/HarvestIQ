from typing import Annotated, Any

from bson import ObjectId
from pydantic import BeforeValidator, ConfigDict, PlainSerializer


def _validate_object_id(value: Any) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value)
    raise ValueError("Invalid ObjectId")


def _serialize_object_id(value: ObjectId) -> str:
    return str(value)


PyObjectId = Annotated[
    ObjectId,
    BeforeValidator(_validate_object_id),
    PlainSerializer(_serialize_object_id, return_type=str),
]

MongoModelConfig = ConfigDict(
    populate_by_name=True,
    arbitrary_types_allowed=True,
    json_encoders={ObjectId: str},
)

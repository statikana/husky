from dataclasses import dataclass as dc_dataclass
from dataclasses import fields as dc_fields
import datetime
from abc import ABC
from typing import Any, Type, TypeVar
from enum import Enum

AnyDataClass = TypeVar("AnyDataClass", bound=Type[dc_dataclass])


class Response(Enum):
    OK = 1
    OK_DELETED = 2
    OK_UPDATED = 3
    ERROR = 4
    ERROR_NOT_FOUND = 5
    ERROR_ALREADY_EXISTS = 6

    YES = 7
    NO = 8
    CANCEL = 9


@dc_dataclass
class Task:
    task_id: int
    user_id: int
    task: str
    date: datetime.date | None
    time: datetime.time | None
    remind_type: int
    datetime_created: datetime.datetime


def autowrap(
    dc: AnyDataClass, data: dict[str, Any], ignore_missing_attrs: bool = False
) -> AnyDataClass:
    fields = dc_fields(dc)
    kwargs = {}
    for f in fields:
        try:
            kwargs[f.name] = data[f.name]
        except KeyError as e:
            if ignore_missing_attrs:
                continue
            raise KeyError(
                f"Dataclass attribute '{f.name}' ({f}) missing from input data"
            ) from e
    return dc(**kwargs)

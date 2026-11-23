"""Shared schema building blocks."""

from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, StringConstraints

T = TypeVar("T")


def _blank_to_none(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


# Optional text field: trims whitespace, turns "" into None (forms send empty strings).
OptStr = Annotated[str | None, BeforeValidator(_blank_to_none)]
OptEmail = Annotated[EmailStr | None, BeforeValidator(_blank_to_none)]
RequiredStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
# Uppercase *before* the pattern check (StringConstraints checks the pattern on the raw value).
CurrencyCode = Annotated[
    str,
    BeforeValidator(lambda v: v.strip().upper() if isinstance(v, str) else v),
    StringConstraints(pattern=r"^[A-Z]{3}$"),
]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class PageParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

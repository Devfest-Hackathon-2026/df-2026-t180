from datetime import datetime, timedelta
from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

NonEmptyString = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]


def _require_utc(value: datetime) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("datetime must be in UTC")
    return value


# Firestore には UTC で保存し、JST への変換は表示するときだけ行う。
UtcDatetime = Annotated[AwareDatetime, AfterValidator(_require_utc)]


class LocalizedStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ja: NonEmptyString
    en: NonEmptyString


# ルールが特定の場所に紐づくときの位置。地域全体のルールでは None にする。
class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)

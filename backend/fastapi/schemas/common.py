from datetime import datetime, timedelta
from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
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

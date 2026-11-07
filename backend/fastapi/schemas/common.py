from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]


class LocalizedStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ja: NonEmptyString
    en: NonEmptyString

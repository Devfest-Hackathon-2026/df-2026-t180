from pydantic import BaseModel, ConfigDict

from schemas.common import NonEmptyString


class Admin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    firebase_uid: NonEmptyString
    employee_name: NonEmptyString

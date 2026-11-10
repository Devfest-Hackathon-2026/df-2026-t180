from typing import Literal

from pydantic import BaseModel, ConfigDict

from schemas.common import LocalizedStatement, Location, NonEmptyString, UtcDatetime


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    region: NonEmptyString
    statement: LocalizedStatement
    updated_at: UtcDatetime
    last_reviewed_at: UtcDatetime | None = None
    location: Location | None = None
    # 地域ガイドのタブ（マナー・交通・暮らし）と、ピンのシートに出す場所名（#22）。
    # どちらも任意。ないルールは「すべて」にだけ表示し、シートの見出しは地域名にする。
    category: Literal["manners", "transport", "living"] | None = None
    place: LocalizedStatement | None = None

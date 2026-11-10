import hashlib
import json

import pytest

from schemas.rule import Rule
from services.rule_versions import rule_version

# PR #46 より前の Rule.model_dump(mode="json") と同じフィールド・値。
# 新しいモデルから除外して作らず、旧形式のシリアライズを独立して固定する。
LEGACY_RULE = {
    "id": "rule_1",
    "region": "sakai",
    "statement": {"ja": "静かにしてください。", "en": "Please keep quiet."},
    "updated_at": "2026-11-07T00:00:00Z",
    "last_reviewed_at": None,
    "location": None,
}


def legacy_version(fields):
    data = json.dumps(fields, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(data.encode()).hexdigest()[:16]


@pytest.mark.parametrize("location", [None, {"lat": 34.57, "lng": 135.48}])
@pytest.mark.parametrize("last_reviewed_at", [None, "2026-11-08T00:00:00Z"])
def test_unset_metadata_preserves_legacy_serialization(location, last_reviewed_at):
    fields = {
        **LEGACY_RULE,
        "location": location,
        "last_reviewed_at": last_reviewed_at,
    }
    expected = legacy_version(fields)
    assert rule_version(Rule.model_validate(fields)) == expected
    assert (
        rule_version(Rule.model_validate({**fields, "category": None, "place": None}))
        == expected
    )


@pytest.mark.parametrize(
    ("before", "after"),
    [(None, "manners"), ("manners", "transport"), ("manners", None)],
)
def test_category_changes_version(before, after):
    fields = {**LEGACY_RULE, "place": {"ja": "公園", "en": "Park"}}
    assert rule_version(
        Rule.model_validate({**fields, "category": before})
    ) != rule_version(Rule.model_validate({**fields, "category": after}))


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (None, {"ja": "公園", "en": "Park"}),
        ({"ja": "公園", "en": "Park"}, {"ja": "駅", "en": "Station"}),
        ({"ja": "公園", "en": "Park"}, None),
    ],
)
def test_place_changes_version(before, after):
    fields = {**LEGACY_RULE, "category": "manners"}
    assert rule_version(
        Rule.model_validate({**fields, "place": before})
    ) != rule_version(Rule.model_validate({**fields, "place": after}))


def test_statement_changes_version():
    rule = Rule.model_validate(LEGACY_RULE)
    edited = Rule.model_validate(
        {**LEGACY_RULE, "statement": {"ja": "新しい本文。", "en": "New text."}}
    )
    assert rule_version(rule) != rule_version(edited)

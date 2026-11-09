"""公開ルールの版（version）の計算。機能B（候補の生成）と機能D（採否・編集）で共通に使う。

版はルールの保存内容から計算するので、共通のスキーマに項目を足さずに使える。
内容が 1 か所でも変わると値が変わる（管理者の書き込みは必ず updated_at か
last_reviewed_at を進めるため、どの書き込みでも変わる）。
"""

import hashlib
import json

from schemas.rule import Rule


def rule_version(rule: Rule) -> str:
    """ルールの保存内容から計算する版。内容が 1 か所でも変わると値が変わる。"""
    data = json.dumps(rule.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(data.encode()).hexdigest()[:16]

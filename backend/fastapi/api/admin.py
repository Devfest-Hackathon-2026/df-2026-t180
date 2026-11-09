"""管理者 API（機能D）。すべて Firebase ID トークンと admins コレクションで認可する。"""

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from repositories.admin import AdminRepository, AdminTransaction, get_admin_repository
from schemas.admin import (
    AdminCandidate,
    CandidateDecision,
    CandidateDecisionResult,
    CandidatePost,
    CandidateTarget,
    RuleEdit,
)
from schemas.rule import Rule
from services.admin_decisions import DecisionConflict, decide_candidate, edit_rule
from services.firebase_auth import (
    AuthNotConfigured,
    InvalidToken,
    TokenVerifier,
    get_token_verifier,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])
bearer = HTTPBearer(auto_error=False)

Repository = Annotated[AdminRepository, Depends(get_admin_repository)]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _verifier() -> TokenVerifier:
    try:
        return get_token_verifier()
    except AuthNotConfigured:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Admin sign-in is not configured"
        ) from None


def signed_in_uid(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    verifier: Annotated[TokenVerifier, Depends(_verifier)],
) -> str:
    """Authorization: Bearer <Firebase ID トークン> を検証して UID を返す。

    トークンがない・無効なら 401。

    DB に触れる前に判定するため、管理者の確認（require_admin）とは分けている。
    """
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Sign in as an admin",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        return verifier(credentials.credentials)
    except InvalidToken:
        raise unauthorized from None


def require_admin(
    uid: Annotated[str, Depends(signed_in_uid)],
    repository: Repository,
) -> str:
    """ログイン済みの UID が admins に登録されているか確認する。なければ 403。"""
    if not repository.is_admin(uid):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not an admin")
    return uid


AdminUid = Annotated[str, Depends(require_admin)]
Now = Annotated[datetime, Depends(utc_now)]


@router.get("/candidates")
def list_candidates(
    _: AdminUid,
    repository: Repository,
    status_filter: Annotated[
        Literal["pending", "approved", "rejected", "all"], Query(alias="status")
    ] = "pending",
    type: Literal["add", "update", "review"] | None = None,
    region: str | None = None,
) -> list[AdminCandidate]:
    """候補の一覧。既定は確認待ち(pending)のみ。元の投稿と対象ルールの現在の内容を添える。"""
    candidates = repository.list_candidates(
        status=None if status_filter == "all" else status_filter,
        type=type,
        region=region,
    )
    posts = repository.get_posts(c.post_id for c in candidates if c.post_id)
    rules = repository.get_rules(
        c.target_rule_id for c in candidates if c.target_rule_id
    )

    result = []
    for candidate in candidates:
        post = posts.get(candidate.post_id) if candidate.post_id else None
        rule = rules.get(candidate.target_rule_id) if candidate.target_rule_id else None
        result.append(
            AdminCandidate(
                **candidate.model_dump(),
                post=CandidatePost(
                    **post.model_dump(include={"text", "reason", "created_at"})
                )
                if post
                else None,
                current=CandidateTarget(
                    **rule.model_dump(
                        include={"statement", "updated_at", "last_reviewed_at"}
                    )
                )
                if rule
                else None,
            )
        )
    return result


@router.patch("/candidates/{candidate_id}")
def decide(
    candidate_id: str,
    decision: CandidateDecision,
    _: AdminUid,
    repository: Repository,
    now: Now,
) -> CandidateDecisionResult:
    """候補を採用・却下する。

    候補の更新と公開ルールの作成・更新を 1 つのトランザクションで行う。

    見つからなければ 404、すでに判断済み・対象ルールがなければ 409。
    """

    def work(tx: AdminTransaction) -> CandidateDecisionResult:
        candidate = tx.get_candidate(candidate_id)
        if candidate is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")
        target = (
            tx.get_rule(candidate.target_rule_id) if candidate.target_rule_id else None
        )
        new_rule_id = tx.new_rule_id() if candidate.type == "add" else ""
        try:
            decided, rule = decide_candidate(
                candidate, target, decision, now=now, new_rule_id=new_rule_id
            )
        except DecisionConflict as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None
        tx.set_candidate(decided)
        if rule is not None:
            tx.set_rule(rule)
        return CandidateDecisionResult(candidate=decided, rule=rule)

    return repository.run_transaction(work)


@router.get("/rules")
def list_rules(
    _: AdminUid,
    repository: Repository,
    region: str | None = None,
) -> list[Rule]:
    """公開ルールの一覧（編集画面用）。新しく更新されたものから。"""
    return repository.list_rules(region=region)


@router.patch("/rules/{rule_id}")
def update_rule(
    rule_id: str,
    edit: RuleEdit,
    _: AdminUid,
    repository: Repository,
    now: Now,
) -> Rule:
    """公開ルールの文を管理者が直接編集する。updated_at を現在時刻に更新する。"""

    def work(tx: AdminTransaction) -> Rule:
        rule = tx.get_rule(rule_id)
        if rule is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
        edited = edit_rule(rule, edit.statement, now=now)
        tx.set_rule(edited)
        return edited

    return repository.run_transaction(work)

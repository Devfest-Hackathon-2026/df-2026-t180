"""管理者 API（機能D）。すべて Firebase ID トークンと admins コレクションで認可する。"""

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from repositories.admin import (
    AdminRepository,
    AdminTransaction,
    TransactionContention,
    get_admin_repository,
)
from schemas.admin import (
    AdminCandidate,
    AdminRule,
    CandidateDecision,
    CandidateDecisionResult,
    CandidatePost,
    CandidateTarget,
    RuleEdit,
)
from schemas.rule import Rule
from services.admin_decisions import (
    DecisionConflict,
    DecisionInvalid,
    decide_candidate,
    edit_rule,
    rule_version,
)
from services.firebase_auth import (
    AuthNotConfigured,
    AuthUnavailable,
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
    """トークンを検証する関数。

    設定（プロジェクトID）の確認はトークンを受け取ってから行う。トークンがなければ、
    設定がなくても 401 にするため。
    """

    def verify(token: str) -> str:
        return get_token_verifier()(token)

    return verify


def signed_in_uid(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    verifier: Annotated[TokenVerifier, Depends(_verifier)],
) -> str:
    """Authorization: Bearer <Firebase ID トークン> を検証して UID を返す。

    - トークンがない・無効: 401
    - 検証の設定がない、Google の公開鍵を取得できない: 503（トークンの問題ではない）

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
    except AuthNotConfigured:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Admin sign-in is not configured"
        ) from None
    except AuthUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Admin sign-in is unavailable"
        ) from None


def require_admin(
    uid: Annotated[str, Depends(signed_in_uid)],
    repository: Repository,
) -> str:
    """ログイン済みの UID が admins に登録されているか確認する。なければ 403。

    管理者権限の取り消しは admins から UID を削除して行う。毎回確認するので、
    削除した次のリクエストから 403 になる。
    """
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
        version = rule_version(rule) if rule else None
        result.append(
            AdminCandidate(
                **candidate.model_dump(),
                rule_changed_since_generated=(
                    version is not None
                    and candidate.target_rule_version is not None
                    and candidate.target_rule_version != version
                ),
                post=CandidatePost(
                    **post.model_dump(include={"text", "reason", "created_at"})
                )
                if post
                else None,
                current=CandidateTarget(
                    **rule.model_dump(
                        include={"statement", "updated_at", "last_reviewed_at"}
                    ),
                    version=version,
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

    - 候補が見つからない: 404
    - 判断済み、対象ルールがない・別の地域・version が変わっている: 409
      （このときは何も書き込まない）
    - update・review の採用で expected_version がない: 422
    - 却下は対象ルールがなくてもできる
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
        except DecisionInvalid as error:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)
            ) from None
        tx.update_candidate(candidate, decided)
        if rule is not None:
            tx.save_rule(target, rule)
        return CandidateDecisionResult(
            candidate=decided, rule=_with_version(rule) if rule else None
        )

    return _run(repository, work)


def _run(repository: AdminRepository, work):
    """トランザクションを実行する。同時の変更が続いて確定できなければ 409。"""
    try:
        return repository.run_transaction(work)
    except TransactionContention:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Changed by someone else. Reload and try again"
        ) from None


def _with_version(rule: Rule) -> AdminRule:
    return AdminRule(**rule.model_dump(), version=rule_version(rule))


@router.get("/rules")
def list_rules(
    _: AdminUid,
    repository: Repository,
    region: str | None = None,
) -> list[AdminRule]:
    """公開ルールの一覧（編集画面用）。新しく更新されたものから。"""
    return [_with_version(rule) for rule in repository.list_rules(region=region)]


@router.patch("/rules/{rule_id}")
def update_rule(
    rule_id: str,
    edit: RuleEdit,
    _: AdminUid,
    repository: Repository,
    now: Now,
) -> AdminRule:
    """公開ルールの文を管理者が直接編集する。updated_at を現在時刻に更新する。

    表示していたときから内容が変わっていれば（expected_version の不一致）409。
    """

    def work(tx: AdminTransaction) -> AdminRule:
        rule = tx.get_rule(rule_id)
        if rule is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
        try:
            edited = edit_rule(rule, edit, now=now)
        except DecisionConflict as error:
            raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None
        tx.save_rule(rule, edited)
        return _with_version(edited)

    return _run(repository, work)

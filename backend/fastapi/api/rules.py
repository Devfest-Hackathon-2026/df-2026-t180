from typing import Annotated

from fastapi import APIRouter, Depends

from repositories.rules import RuleRepository, get_rule_repository
from schemas.rule import Rule

router = APIRouter()


@router.get("/api/regions/{region_id}/rules")
def list_region_rules(
    region_id: str,
    repository: Annotated[RuleRepository, Depends(get_rule_repository)],
) -> list[Rule]:
    return repository.list_by_region(region_id)

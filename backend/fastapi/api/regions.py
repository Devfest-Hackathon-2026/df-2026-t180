from typing import Annotated

from fastapi import APIRouter, Depends

from repositories.regions import RegionRepository, get_region_repository
from schemas.region import Region

router = APIRouter()


# 地域は数件なので全件を返し、地域名での検索はフロントで行う。
@router.get("/api/regions")
def list_regions(
    repository: Annotated[RegionRepository, Depends(get_region_repository)],
) -> list[Region]:
    return repository.list_all()

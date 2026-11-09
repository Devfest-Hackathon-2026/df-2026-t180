from fastapi import FastAPI

from api import admin, posts, regions, rules

app = FastAPI(title="Regional Rules API")
app.include_router(posts.router)
app.include_router(regions.router)
app.include_router(rules.router)
app.include_router(admin.router)

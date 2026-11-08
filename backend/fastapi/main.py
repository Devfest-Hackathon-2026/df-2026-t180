from fastapi import FastAPI

from api import posts

app = FastAPI(title="Regional Rules API")
app.include_router(posts.router)

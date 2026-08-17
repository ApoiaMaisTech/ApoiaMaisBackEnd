from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.users import router as users_router
from app.api.routes.auth import router as auth_router



app = FastAPI(
    title="ApoiaMais API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

@app.get("/")
def read_root():
    return {"message": "ApoiaMais Backend rodando com sucesso no Docker!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "connected"}
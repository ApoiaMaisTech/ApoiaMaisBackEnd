from fastapi import FastAPI

app = FastAPI(
    title="ApoiaMais API",
    version="1.0.0"
)

@app.include_router(prefix="/users", tags=["Users"])
@app.include_router(prefix="/auth", tags=["Auth"])

@app.get("/")
def read_root():
    return {"message": "ApoiaMais Backend rodando com sucesso no Docker!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "connected"}


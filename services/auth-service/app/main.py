from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from . import crud, schemas
from .database import get_db

app = FastAPI(
    title="ApoiaMais Auth Service",
    servers=[{"url": "http://localhost:8000", "description": "Servidor Local"}]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erro interno do servidor: {str(exc)}"},
    )

@app.post("/registrar", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def registrar(user: schemas.UserCreate, db: Session = Depends(get_db)):
    
    if crud.get_user_by_email(db, email=user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="E-mail já cadastrado"
        )
    
    return crud.create_user(db=db, user=user)

@app.get("/health")
def health():
    return {"status": "Auth Service Online"}
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from . import crud, schemas, database

app = FastAPI(title="User Service - ApoiaMais", version="1.0.0")

# CORS configurado para o React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "user-service"}

# Rota de Criação com tratamento de erro
@app.post("/pacientes/", response_model=schemas.Paciente, status_code=status.HTTP_201_CREATED)
def create_paciente(paciente: schemas.PacienteCreate, db: Session = Depends(database.get_db)):
    db_paciente = crud.create_paciente(db, paciente)
    if not db_paciente:
        raise HTTPException(status_code=400, detail="Erro ao criar paciente")
    return db_paciente

# Rota de listagem
@app.get("/pacientes/", response_model=List[schemas.Paciente])
def read_pacientes(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    pacientes = crud.get_pacientes(db, skip=skip, limit=limit)
    return pacientes

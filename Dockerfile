FROM python:3.11-slim

WORKDIR /app

# Instala dependências essenciais do sistema para compilar pacotes 
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de dependências da raiz para o container
COPY requirements.txt .

# dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# O código do seu app será montado via volume no docker-compose, 
# mas copiamos por garantia para ambientes de produção
COPY . /app

# Comando para rodar o FastAPI apontando para o main.py dentro da pasta app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
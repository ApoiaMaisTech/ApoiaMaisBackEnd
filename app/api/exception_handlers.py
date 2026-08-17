from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.exceptions.base import DomainException

# registra excecoes globais mp navegador
def register_exception_handlers(app: FastAPI):

    # usa o construtor base de excecoes como argumento
    @app.exception_handler(DomainException)
    async def domain_exception_handler(
        request: Request,
        exc: DomainException
    ):
        # retorna o erro expecifico em json caso tenha algo errado na requisicao
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": exc.message,
                "errors": []
            }
        )
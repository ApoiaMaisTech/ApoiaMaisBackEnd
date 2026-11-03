class DomainException(Exception):
    # status HTTP e código estável usados pelo handler global; cada subclasse define os seus.
    # O frontend deve decidir pelo `code` (contrato), nunca pelo texto de `message`.
    status_code: int = 400
    code: str = "BAD_REQUEST"
    default_message: str = "Requisição inválida."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)

class DomainException(Exception):
    # status HTTP usado pelo handler global; cada subclasse define o seu
    status_code: int = 400
    default_message: str = "Requisição inválida."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)

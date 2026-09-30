# app/application/use_cases/reports/

Reservado para os casos de uso de relatórios. **Ainda não implementado.**

## Estado atual

| Arquivo                     | Conteúdo |
|-----------------------------|----------|
| `create_report_request.py`  | Vazio |
| `report_response.py`        | Vazio |

Não existe model, repositório, caso de uso nem rota de relatórios. O arquivo `app/api/routes/reports.py` também está vazio e não é registrado em `main.py`.

## Ao implementar

Siga o mesmo padrão do módulo de usuários:

1. DTOs de entrada e saída em `app/application/dto/` (ou nesta pasta, se forem exclusivos de relatórios).
2. Interface do repositório em `app/domain/repositories/`.
3. Model e repositório SQLAlchemy em `app/infrastructure/database/`, com migration Alembic.
4. Um caso de uso por ação nesta pasta.
5. Fábricas em `app/api/dependencies/use_cases.py` e router em `app/api/routes/reports.py`, registrado em `main.py`.
6. Testes unitários do caso de uso e testes de autorização da rota.

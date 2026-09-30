# docs/

Recursos estáticos usados na documentação do backend.

## Conteúdo

```text
docs/
└── images/
    └── demo.gif      Demonstração visual usada no README principal
```

## Onde está a documentação técnica

A documentação da arquitetura fica junto do código, em um README por pasta:

| Tema | Documento |
|------|-----------|
| Visão geral das camadas e funcionalidades | [`../app/README.md`](../app/README.md) |
| Rotas, autenticação e tratamento de erros | [`../app/api/README.md`](../app/api/README.md), [`../app/api/routes/README.md`](../app/api/routes/README.md) |
| Casos de uso e DTOs | [`../app/application/README.md`](../app/application/README.md) |
| Configuração e variáveis de ambiente | [`../app/core/README.md`](../app/core/README.md) |
| Entidades, enums, exceções e interfaces | [`../app/domain/README.md`](../app/domain/README.md) |
| Banco de dados, models e repositórios | [`../app/infrastructure/database/README.md`](../app/infrastructure/database/README.md) |
| JWT e hash de senha | [`../app/infrastructure/security/README.md`](../app/infrastructure/security/README.md) |
| Migrations | [`../app/alembic/README`](../app/alembic/README) |
| Testes | [`../tests/README.md`](../tests/README.md) |

O contrato OpenAPI publicado fica no repositório de integração ([ApoiaMaisTech/ApoiaMais](https://github.com/ApoiaMaisTech/ApoiaMais)), em `contratos/auth-service.yaml`.

## Convenções

- Imagens em `.png`, `.svg` ou `.gif`, com nomes descritivos (`fluxo-login.svg`, `diagrama-er.png`).
- Diagramas preferencialmente em `.svg`, ou com o arquivo-fonte versionado junto.
- Evite binários grandes; use links externos quando possível.
- Não armazene credenciais nem dados pessoais nesta pasta.

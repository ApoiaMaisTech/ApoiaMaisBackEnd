# ⚙️ app/application/use_cases/

O diretório `use_cases/` contém a **camada de aplicação** do sistema. Aqui residem os **casos de uso** — classes responsáveis por orquestrar as regras de negócio, coordenar repositórios e retornar resultados para a camada de interface.

Esta camada é o coração da arquitetura, sendo completamente independente de frameworks, banco de dados e detalhes de infraestrutura.

---

## 🗂️ Estrutura

```text
use_cases/
├── reports/          # Casos de uso do domínio de relatórios
└── users/            # Casos de uso do domínio de usuários
```

---

## 🏛️ Responsabilidade

Cada **Use Case** representa uma única ação de negócio e deve:

1. Receber dados de entrada (DTOs ou Schemas)
2. Aplicar as regras de negócio
3. Interagir com repositórios ou serviços externos
4. Retornar um resultado ou lançar uma exceção de domínio

---

## 📐 Padrão de Implementação

```python
from app.domain.exceptions import UserNotFoundException

class GetUserByIdUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, user_id: int):
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise UserNotFoundException(user_id)
        return user
```

---

## 📋 Princípios desta Camada

| Princípio                 | Descrição                                                                 |
|---------------------------|---------------------------------------------------------------------------|
| **Single Responsibility** | Um Use Case = Uma ação de negócio                                         |
| **Independência**         | Sem importações de `api/` ou `infrastructure/` diretas                   |
| **Testabilidade**         | Toda dependência deve ser injetada, facilitando mocks em testes unitários |
| **Clareza**               | O nome do Use Case deve descrever exatamente o que ele faz               |

---

## 📂 Subdiretórios

| Diretório   | Descrição                                         |
|-------------|---------------------------------------------------|
| `reports/`  | Geração, listagem e exportação de relatórios      |
| `users/`    | Criação, autenticação e gerenciamento de usuários |

> 📂 Veja: [`reports/README.md`](./reports/README.md) · [`users/README.md`](./users/README.md)
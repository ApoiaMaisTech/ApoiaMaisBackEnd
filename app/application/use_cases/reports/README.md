# 📊 app/application/use_cases/reports/

O diretório `reports/` contém os **casos de uso** relacionados à geração, consulta e exportação de **relatórios** dentro da plataforma ApoiaMais.

---

## 🗂️ Estrutura

```text
reports/
├── create_report.py          # Criação de novo relatório
├── get_report_by_id.py       # Consulta de relatório por ID
├── list_reports.py           # Listagem paginada de relatórios
├── export_report.py          # Exportação de relatório (PDF, CSV, etc.)
└── delete_report.py          # Remoção de relatório
```

---

## 📋 Casos de Uso

### `CreateReportUseCase`
Responsável por criar um novo relatório a partir dos dados fornecidos.

**Entradas:** dados do relatório (título, período, tipo, usuário responsável)  
**Saída:** relatório criado com ID gerado  
**Exceções:** `InvalidReportDataException`, `UnauthorizedException`

---

### `GetReportByIdUseCase`
Busca um relatório específico pelo seu identificador único.

**Entradas:** `report_id: int`  
**Saída:** entidade de relatório  
**Exceções:** `ReportNotFoundException`

---

### `ListReportsUseCase`
Retorna uma lista paginada de relatórios, com suporte a filtros por período, tipo e usuário.

**Entradas:** filtros e parâmetros de paginação  
**Saída:** lista paginada de relatórios

---

### `ExportReportUseCase`
Exporta um relatório para um formato específico (PDF, CSV, XLSX).

**Entradas:** `report_id: int`, `format: str`  
**Saída:** arquivo binário ou URL de download  
**Exceções:** `ReportNotFoundException`, `UnsupportedFormatException`

---

### `DeleteReportUseCase`
Remove um relatório do sistema, verificando permissões do usuário solicitante.

**Entradas:** `report_id: int`, `current_user`  
**Saída:** confirmação de remoção  
**Exceções:** `ReportNotFoundException`, `UnauthorizedException`

---

## 🔗 Dependências

| Recurso                    | Descrição                               |
|----------------------------|-----------------------------------------|
| `domain/exceptions.py`     | Exceções específicas do domínio         |
| `infrastructure/database/` | Repositório de relatórios               |
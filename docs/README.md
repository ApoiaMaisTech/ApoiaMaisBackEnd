# 📚 docs/

O diretório `docs/` centraliza toda a **documentação estática** do projeto **ApoiaMais Backend**, incluindo imagens, diagramas, fluxos e demais recursos visuais utilizados nos READMEs e na documentação técnica.

---

## 🗂️ Estrutura

```text
docs/
└── images/           # Imagens, GIFs e diagramas do projeto
    └── demo.gif      # Demonstração visual da aplicação
```

---

## 📂 Subdiretórios

### `images/`
Armazena todos os recursos visuais utilizados na documentação:

| Arquivo      | Descrição                                         |
|--------------|---------------------------------------------------|
| `demo.gif`   | GIF de demonstração do funcionamento da aplicação |

> 📂 Veja: [`images/README.md`](./images/README.md)

---

## 📋 Convenções

- ✅ Imagens em formato `.png`, `.jpg`, `.gif` ou `.svg`
- ✅ Diagramas de arquitetura podem ser exportados como `.svg` ou `.png`
- ✅ Nomeie os arquivos de forma descritiva: `auth-flow-diagram.png`, `er-diagram.svg`
- ❌ Não versione arquivos binários grandes — utilize LFS ou links externos
- ❌ Não armazene documentos sensíveis ou credenciais neste diretório

---

## 🔗 Como referenciar no README

```markdown
<img src="./docs/images/demo.gif" alt="Demo ApoiaMais" width="800" />
```
# danielhsf-agent-skills

Coleção de [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) para uso com o Claude Code. Cada skill vive em seu próprio diretório sob `skills/`, contendo um `SKILL.md` (instruções e metadados) e quaisquer scripts de apoio.

## Skills disponíveis

| Skill | Descrição |
| --- | --- |
| [`summarize-paper-pt`](skills/summarize-paper-pt/) | Lê um artigo acadêmico em PDF e gera um resumo conciso e bem estruturado em português (pt-BR), salvo como arquivo markdown. |

## Estrutura do repositório

```
danielhsf-agent-skills/
├── README.md                 # este arquivo
└── skills/
    └── summarize-paper-pt/
        ├── SKILL.md          # instruções + metadados da skill
        └── scripts/          # scripts de apoio
```

## Como usar uma skill

Copie (ou faça um symlink de) o diretório da skill para o seu diretório de skills do Claude Code:

```bash
ln -s "$(pwd)/skills/summarize-paper-pt" ~/.claude/skills/summarize-paper-pt
```

Cada skill é autocontida — consulte o `SKILL.md` correspondente para dependências e detalhes de uso.

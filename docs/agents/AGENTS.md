# 🤖 AGENTS.md — WOCOTM Academy
## Spec Driven Development — Definição de Agentes

---

## Quantos agentes?

**4 agentes fixos** por ciclo de sprint. Nenhum a mais — cada agente tem contexto mínimo e responsabilidade única.

---

## Agentes e Responsabilidades

### 🧠 AGENT-1 — Architect (você, humano)
**Papel:** Dono do produto e do processo. Não consome janela de contexto de LLM.

Responsabilidades:
- Escreve e mantém o `SPEC.md` (estrutura definida abaixo)
- Decide quais sprints executar e em qual ordem
- Aprova ou rejeita o `PROGRESS.md` ao final de cada ciclo
- Único que tem visão completa do projeto

Input necessário: PRD.md, feedback de produto, bugs reportados
Output: SPEC.md atualizado, número da sprint a executar

---

### 💻 AGENT-2 — Coder
**Papel:** Implementa as features da sprint. Contexto cirúrgico — recebe apenas o necessário.

**ID:** `coder-agent`

Input obrigatório (e suficiente):
```
- SPEC.md (seções: stack, data models, API spec, file structure, sprint atual)
- PROGRESS.md (estado atual do projeto)
- Número da sprint
```

Responsabilidades:
- Lê apenas a sprint corrente no SPEC.md
- Implementa os features listados
- Roda: `pytest` + `ruff` (lint) + verificação de imports
- Nunca consulta sprints passadas ou futuras
- Ao terminar: gera diff/lista de arquivos alterados

Output: código implementado + `CODER_REPORT.md` (o que foi feito, o que não foi, bloqueios)

---

### 🔍 AGENT-3 — Evaluator
**Papel:** Valida cada acceptance criterion da sprint. Contexto mínimo — só vê critérios e código.

**ID:** `evaluator-agent`

Input obrigatório:
```
- SPEC.md (apenas: features + acceptance criteria da sprint atual)
- CODER_REPORT.md
- Arquivos de código alterados (apenas os listados no CODER_REPORT)
```

Responsabilidades:
- Para cada acceptance criterion: emite `PASS` ou `FAIL`
- Se `FAIL`: escreve feedback específico com localização do problema (arquivo + linha)
- Devolve ao Coder com instrução de correção (máximo 2 ciclos de correção por sprint)
- Se após 2 correções ainda `FAIL`: escalona para Architect com diagnóstico

Output: `EVAL_REPORT.md` com tabela de critérios

---

### 📋 AGENT-4 — Progress Tracker
**Papel:** Atualiza o PROGRESS.md para a próxima sprint. Contexto mínimo.

**ID:** `progress-agent`

Input obrigatório:
```
- PROGRESS.md atual
- EVAL_REPORT.md
- CODER_REPORT.md
```

Responsabilidades:
- Marca features como `DONE`, `PARTIAL` ou `BLOCKED`
- Atualiza lista de arquivos existentes (file tree)
- Registra bugs conhecidos e débitos técnicos
- Gera resumo de 3 linhas para contexto da próxima sprint

Output: `PROGRESS.md` atualizado (este é o único arquivo que viaja entre sprints)

---

## Ciclo de Sprint (diagrama)

```
ARCHITECT (você)
     │
     ▼
[SPEC.md + sprint_number + PROGRESS.md]
     │
     ▼
CODER ──────────────────────────────────────────────────┐
(implementa + pytest + ruff)                            │
     │                                                  │
     ▼                                                  │
EVALUATOR                                               │
(PASS/FAIL por critério)                                │
     │                                                  │
     ├── algum FAIL? ─── feedback ──────────────────────┘
     │                   (max 2x)
     │
     ▼ (todos PASS ou escalonado)
PROGRESS TRACKER
(atualiza PROGRESS.md)
     │
     ▼
PRÓXIMA SPRINT
(contexto zerado, apenas PROGRESS.md viaja)
```

---

## Economia de Contexto — Regras

| Regra | Motivo |
|---|---|
| Coder recebe apenas a sprint atual do SPEC | Sprints passadas = ruído |
| Evaluator recebe apenas os arquivos alterados | Ler toda a codebase = desperdício |
| PROGRESS.md tem limite de 150 linhas | Arquivo leve que viaja entre sprints |
| Nenhum agente lê o PRD.md | O PRD já foi destilado no SPEC |
| Coder nunca abre arquivos não listados no file structure | Evita exploração desnecessária |

---

## Identificadores de Agente por Sprint (SPEC.md)

Cada sprint no SPEC.md declara:
```yaml
coder_agent_id: coder-agent
evaluator_agent_id: evaluator-agent
progress_agent_id: progress-agent
```

Isso permite rastrear qual agente executou cada sprint no PROGRESS.md.

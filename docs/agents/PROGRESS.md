# 📋 PROGRESS.md — WOCOTM Academy
## Estado do Projeto (atualizado por: progress-agent)

**Sprint atual:** S8 concluída (S9 pendente)
**Última atualização:** 2026-04-16
**Status geral:** 🟢 Funcional — Sprints S1–S8 implementadas

---

## Resumo para Próxima Sprint

> S9 — Hardening. O projeto está funcionalmente completo (S1–S8 entregues).
> Pendente: criar suite `pytest`, rodar `ruff` lint, auditoria de segurança, `exporters.py`.
> Banco operacional em PostgreSQL/SQLite. Chave Groq dinâmica por instrutor implementada.

---

## Features por Sprint

| Sprint | Status | Features concluídas | Pendências / Bugs |
|--------|--------|---------------------|-------------------|
| S1 | ✅ Concluída | F1.1–F1.8 (todas) | — |
| S2 | ✅ Concluída | F2.1–F2.8 (todas) | — |
| S3 | ✅ Concluída | F3.1–F3.7 (todas) | — |
| S4 | ✅ Concluída | F4.1–F4.4 (todas) | — |
| S5 | ✅ Concluída | F5.1–F5.8 (todas) | — |
| S6 | ✅ Concluída | F6.1–F6.7 (todas) | — |
| S7 | ✅ Concluída | F7.1–F7.3 (todas) | — |
| S8 | ✅ Concluída | F8.1–F8.5 (todas) | — |
| S9 | ⬜ Não iniciada | — | pytest, ruff, exporters.py |

---

## Detalhamento por Sprint

### S1 — Fundação ✅
- `db/models.py` — 13 tabelas: User, AuditLog, UserProgress, Enrollment, Course, Module, Lesson, Quiz, LessonAsset, ChatMessage, LessonChatMessage, UserConsent, ChatbotHistory
- `db/database.py` — Engine SQLAlchemy + `get_db()` context manager + `init_db()`
- `auth.py` — login bcrypt, logout (limpa chatbot_history + audit), deep linking `?course_id=`, `require_role()`, `get_current_user()`
- `config.py` — todas as variáveis de ambiente (Groq, DB, Fernet, SMTP, URL)
- `app.py` — navbar dinâmica por papel (5 papéis), roteamento, `st.cache_resource` para startup

### S2 — Home + Course Creator (Etapas 1 e 2) ✅
- `views/home.py` — catálogo filtrado por papel (estudante: só seus cursos; instrutor: seus cursos; admin: todos), badges de status coloridos, botões View/Delete
- `views/course_creator.py` — wizard 3 etapas com `_init_state()`, `_reset_creator()`
- Etapa 1: formulário tópico + sliders módulos/lições + temas opcionais → `generate_and_save_syllabus()`
- Etapa 2: navegação entre lições via dropdown, slider target_chars, streaming de geração com indicador `▌`, editor texto, `Save & Finalize`
- `services/syllabus_service.py` — geração de syllabus via Groq
- `services/content_service.py` — `generate_lesson_stream()` com chunks
- `services/ai_service.py` — `GroqProvider` com `generate()`, `generate_stream()`, retry 3x em 429
- `repositories/course_repo.py` — CRUD completo cursos/módulos/lições/assets

### S3 — Content Player + LGPD ✅
- `views/content_player.py` — modal consentimento LGPD (`@st.dialog`), sidebar hierárquica módulo/lição, badges ✅ progresso, render Markdown + HTML, galeria imagens (grid 3 col), player vídeo inline, botão download docs, botão "Mark as Complete"
- `services/privacy_service.py` — `has_consented()`, `record_consent()` → tabela `user_consents`
- `repositories/user_repo.py` — `mark_lesson_complete()`, `get_completed_lesson_ids()`, `get_student_progress()`, `log_audit()`, CRUD usuários completo

### S4 — Quiz ✅
- `views/quiz_view.py` — questões via `st.radio`, botão "Check Answer" por questão, feedback ✅/❌ com explicação e resposta correta
- `services/quiz_service.py` — `generate_and_save_quiz()` via Groq
- `repositories/quiz_repo.py` — `get_quizzes()`, `save_quiz()`

### S5 — Tutor AI ✅
- `views/chatbot_view.py` — inicialização do `ChatbotService` por sessão, display histórico decriptado, `st.chat_input`, streaming com `▌`, tratamento de erro de API key
- `services/chatbot_service.py` — `ChatbotService` (modo curso + modo geral), `QuickChatService` (lição específica), detecção de palavras-chave (13 keywords), recomendação de cursos (enrolled vs. not enrolled), persistência criptografada em `chatbot_history`, limite `MAX_CHAT_HISTORY`
- `services/security_service.py` — `EncryptionManager` (Fernet AES-128), `hash_password()`, `verify_password()` (bcrypt)
- Histórico apagado automaticamente no logout

### S6 — Admin Dashboard ✅
- `views/admin_dashboard.py` — 4 abas com acesso hierárquico por papel
- Aba Usuários: tabela com filtro (não-sys-admin não vê outros admins), criar usuário (formulário + audit), editar/deletar (cascade + audit)
- Aba Privacy Audit (sys/privacy admin): justificativa obrigatória, botão bloqueado sem texto, acesso auditado como `VIEW_SENSITIVE_DATA`, tabela decriptada
- Aba Privacy Metrics (general admin): total interações + estudantes únicos (agregado)
- Aba Audit Logs: histórico completo (tempo, ator, ação, detalhes)
- Aba Enrollments: matricular estudante em curso + audit log
- Resolução dinâmica de chave Groq: chave pessoal do instrutor → fallback qualquer instrutor → `.env`

### S7 — Instructor Dashboard ✅
- `views/instructor_dashboard.py` — 2 abas
- Aba Student Progress: tabela aluno/email/curso/concluídas/percentual (instrutor vê seus cursos; admin vê todos)
- Aba Courses Overview: cards expansíveis, botão Open Course, formulário edição metadados (título, sinopse, tags) + audit log

### S8 — Email + Media Assets + Course Creator Etapa 3 ✅
- `services/email_service.py` — SMTP STARTTLS (Outlook 587), template HTML responsivo com credenciais + link plataforma, falha silenciosa se SMTP não configurado
- `views/course_creator.py` — Gerenciador de Mídia: assets existentes com botão ❌ Delete, upload imagem (PNG/JPG/JPEG) com alinhamento/tamanho/posição, upload documento (PDF/DOC/DOCX) com label + posição, upload vídeo (MP4/MOV/WEBM) com opções
- Assets salvos em `static/uploads/` com UUID único
- Etapa 3: botão "Generate AI Quiz" + botão "Skip → Content Player"
- Redirect automático para Content Player ao finalizar o wizard

---

## Arquivos Existentes

```
course_platform/
├── app.py                      ✅ Entry point + navbar + roteamento
├── auth.py                     ✅ Login, logout, deep link, require_role
├── config.py                   ✅ Todas as env vars
├── requirements.txt            ✅
├── seed_admin.py               ✅ Script de seed do admin inicial
├── reset_pg.py                 ✅ Script reset PostgreSQL
├── db/
│   ├── models.py               ✅ 13 tabelas SQLAlchemy
│   └── database.py             ✅ Engine + Session + init_db
├── views/
│   ├── home.py                 ✅ Catálogo de cursos por papel
│   ├── course_creator.py       ✅ Wizard 3 etapas + media manager
│   ├── content_player.py       ✅ Player + LGPD + progresso
│   ├── quiz_view.py            ✅ Quiz player
│   ├── chatbot_view.py         ✅ Tutor AI
│   ├── instructor_dashboard.py ✅ Dashboard instrutor
│   └── admin_dashboard.py      ✅ Painel admin hierárquico
├── services/
│   ├── ai_service.py           ✅ GroqProvider sync+stream+retry+key dinâmica
│   ├── chatbot_service.py      ✅ ChatbotService + QuickChatService
│   ├── content_service.py      ✅ Geração de lições streaming
│   ├── syllabus_service.py     ✅ Geração de syllabus
│   ├── quiz_service.py         ✅ Geração de quizzes
│   ├── email_service.py        ✅ SMTP STARTTLS
│   ├── security_service.py     ✅ Fernet + bcrypt
│   └── privacy_service.py      ✅ LGPD consent
├── repositories/
│   ├── user_repo.py            ✅ CRUD usuários + audit + progresso
│   ├── course_repo.py          ✅ CRUD cursos + módulos + lições + assets
│   └── quiz_repo.py            ✅ CRUD quizzes
├── utils/
│   ├── prompts.py              ✅ System prompts (tutor, geral, quick chat)
│   └── exporters.py            ⬜ Stub — não implementado (S9)
├── static/uploads/             ✅ Assets de mídia com UUID
└── docs/
    ├── PRD.md                  ✅ Documentação completa gerada em 2026-04-16
    └── agents/
        ├── SPEC.md             ✅
        ├── AGENTS.md           ✅
        └── PROGRESS.md         ✅ (este arquivo)
```

---

## Débitos Técnicos

- `utils/exporters.py` existe mas está como stub vazio — implementar em S9
- Sem suite de testes `pytest` ainda — implementar em S9
- Sem lint `ruff` executado formalmente — executar em S9
- `SPEC.md` define `lesson_assets` com campos `alignment`, `size_percent` que diferem ligeiramente do modelo real (`position` apenas) — menor divergência

---

## Bugs Conhecidos

- `DetachedInstanceError` SQLAlchemy — resolvido via MockLesson/MockAsset wrappers que deserializam fora da sessão ativa (`content_player.py`, `course_creator.py`)
- Chave Groq de instrutor não resolvia corretamente na geração de conteúdo — corrigido com propagação de `instructor_id` por todo o pipeline de geração

---

## Decisões de Arquitetura Tomadas

| Decisão | Motivo |
|---|---|
| Fernet (AES-128) para criptografia de chat history | Reversível necessário para exibir histórico ao usuário |
| bcrypt para senhas | Irreversível; padrão da indústria |
| `get_db()` como context manager | Garante commit/rollback automático |
| MockLesson/MockAsset wrappers | Evita `DetachedInstanceError` fora da sessão SQLAlchemy |
| Chave Groq dinâmica (instrutor → fallback → .env) | Cada instrutor usa sua cota pessoal da API |
| Histórico de chat deletado no logout | Conformidade LGPD — dados sensíveis não persistem além da sessão |
| `@st.cache_resource` em `init_db()` | Evita reinicialização do banco a cada rerun do Streamlit |

---

*Arquivo mantido por progress-agent. Limite: 150 linhas. É o único contexto que viaja entre sprints.*

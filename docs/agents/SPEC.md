# 📐 SPEC.md — WOCOTM Academy
## Spec Driven Development

**Versão:** 1.0 | **Projeto:** antigravity/wocotm-academy | **Data:** Abril 2026

> ⚠️ Regra do Coder: leia APENAS a seção da sprint designada + seções globais (6. Stack, 5. Data Models, 8. File Structure). Ignore todas as outras sprints.

---

## 1. Sprints — Divisão do Trabalho

| Sprint | Foco | Prioridade |
|--------|------|------------|
| **S1** | Fundação: DB, Auth, RBAC, Navbar | 🔴 Crítico |
| **S2** | Home (catálogo) + Course Creator Wizard (Etapas 1 e 2) | 🔴 Crítico |
| **S3** | Content Player + Progresso de Lições + LGPD consent | 🔴 Crítico |
| **S4** | Quiz View + Quiz Service + Quiz Repo | 🟠 Alto |
| **S5** | Tutor AI (chatbot geral + modo curso + QuickChat) | 🟠 Alto |
| **S6** | Admin Dashboard (CRUD usuários, Audit, Privacy, Enrollments) | 🟠 Alto |
| **S7** | Instructor Dashboard (progresso alunos + course overview) | 🟡 Médio |
| **S8** | Email service + Course Creator Etapa 3 (quiz) + Media assets | 🟡 Médio |
| **S9** | Hardening: testes E2E, lint total, segurança, exporters | 🟢 Baixo |

---

## 2. Features por Sprint

---

### Sprint 1 — Fundação

**Features:**
- F1.1 — Modelos SQLAlchemy completos (`db/models.py`)
- F1.2 — Engine + Session + `init_db()` (`db/database.py`)
- F1.3 — Login com bcrypt + sessão no `st.session_state`
- F1.4 — Logout com limpeza de histórico de chat + audit log
- F1.5 — Deep linking via `?course_id=<id>`
- F1.6 — `require_role(*roles)` — proteção de rotas
- F1.7 — Navbar dinâmica por papel (app.py)
- F1.8 — `config.py` com todas as variáveis de ambiente

**Coder Agent ID:** `coder-agent`

---

### Sprint 2 — Home + Course Creator (Etapas 1 e 2)

**Features:**
- F2.1 — Home: listagem de cursos por papel (estudante/instrutor/admin)
- F2.2 — Home: cards com título, descrição, badge de status, botões View/Delete
- F2.3 — Course Creator Etapa 1: formulário + geração de syllabus via Groq
- F2.4 — Course Creator Etapa 2: navegação entre lições + geração com streaming
- F2.5 — Course Creator Etapa 2: editor de texto + Save & Finalize
- F2.6 — `syllabus_service.py` + `content_service.py`
- F2.7 — `ai_service.py`: GroqProvider (sync + stream + retry)
- F2.8 — `course_repo.py`: CRUD cursos, módulos, lições

**Coder Agent ID:** `coder-agent`

---

### Sprint 3 — Content Player + LGPD

**Features:**
- F3.1 — Modal de consentimento LGPD (primeiro acesso de estudante)
- F3.2 — Sidebar com hierarquia módulo/lição + badges de progresso
- F3.3 — Renderização de conteúdo Markdown + HTML embutido
- F3.4 — Renderização de assets: imagem (grid 3 col), vídeo inline, doc download
- F3.5 — Botão "Mark as Complete" + salvar em `user_progress`
- F3.6 — `privacy_service.py`: registro de consentimento
- F3.7 — `user_repo.py`: CRUD usuários + progresso + audit log

**Coder Agent ID:** `coder-agent`

---

### Sprint 4 — Quiz

**Features:**
- F4.1 — Quiz view: exibe questões, opções via radio, botão Check Answer por questão
- F4.2 — Feedback imediato: ✅ correto com explicação / ❌ errado com resposta correta
- F4.3 — `quiz_service.py`: geração de quiz via Groq
- F4.4 — `quiz_repo.py`: CRUD de quizzes

**Coder Agent ID:** `coder-agent`

---

### Sprint 5 — Tutor AI

**Features:**
- F5.1 — Chatbot Modo Curso: prompt contextualizado com conteúdo do curso ativo
- F5.2 — Chatbot Modo Geral: catálogo completo + cursos matriculados vs disponíveis
- F5.3 — Persistência criptografada (Fernet) em `chatbot_history`
- F5.4 — Detecção de palavras-chave + recomendação de cursos
- F5.5 — Streaming de resposta com indicador `▌`
- F5.6 — QuickChat por lição (`lesson_chat_messages`)
- F5.7 — `chatbot_service.py` completo
- F5.8 — `security_service.py`: EncryptionManager singleton

**Coder Agent ID:** `coder-agent`

---

### Sprint 6 — Admin Dashboard

**Features:**
- F6.1 — Aba Usuários: tabela + filtro hierárquico por papel de admin
- F6.2 — Criar usuário: formulário + audit log + email de boas-vindas
- F6.3 — Editar/Deletar usuário com cascade + audit log
- F6.4 — Aba Privacy Audit: justificativa obrigatória + logs decriptados (sys_admin / privacy_admin)
- F6.5 — Aba Privacy Metrics: métricas agregadas (general_admin)
- F6.6 — Aba Audit Logs: histórico completo de eventos
- F6.7 — Aba Enrollments: matricular estudante em curso

**Coder Agent ID:** `coder-agent`

---

### Sprint 7 — Instructor Dashboard

**Features:**
- F7.1 — Aba Student Progress: tabela aluno/curso/lições concluídas/%
- F7.2 — Aba Courses Overview: cards expansíveis + botão Open Course
- F7.3 — Formulário de edição de metadados de curso (título, sinopse, tags)

**Coder Agent ID:** `coder-agent`

---

### Sprint 8 — Email + Media Assets + Course Creator Etapa 3

**Features:**
- F8.1 — `email_service.py`: SMTP STARTTLS + template HTML responsivo
- F8.2 — Course Creator: Gerenciador de Mídia por lição (imagem/vídeo/doc)
- F8.3 — Salvamento de assets em `static/uploads/` com UUID
- F8.4 — Course Creator Etapa 3: gerar quiz via Groq ou skip
- F8.5 — Redirect para Content Player após conclusão do wizard

**Coder Agent ID:** `coder-agent`

---

### Sprint 9 — Hardening

**Features:**
- F9.1 — Suite de testes pytest cobrindo serviços e repositórios
- F9.2 — Lint completo com ruff (zero warnings)
- F9.3 — Auditoria de segurança: senhas, chaves, criptografia
- F9.4 — `utils/exporters.py`: exportação de dados
- F9.5 — Verificação de conformidade LGPD nos fluxos críticos

**Coder Agent ID:** `coder-agent`

---

## 3. Acceptance Criteria por Sprint

---

### Sprint 1

| ID | Critério | Método de Validação |
|----|----------|---------------------|
| AC1.1 | Todas as 13 tabelas existem no banco após `init_db()` | `inspect(engine).get_table_names()` |
| AC1.2 | Login com credenciais corretas cria `st.session_state.user` com `id`, `role`, `username` | Teste unitário mock Streamlit |
| AC1.3 | Login com senha errada exibe erro e não cria sessão | Assertion `session_state` vazio |
| AC1.4 | Logout apaga `chatbot_history` do usuário e limpa `session_state` | Query pós-logout retorna 0 rows |
| AC1.5 | `require_role("student")` redireciona admin para home | Teste com role="system_admin" |
| AC1.6 | Navbar mostra itens corretos para cada um dos 5 papéis | Snapshot dos itens renderizados |
| AC1.7 | `config.py` lê todas as variáveis do `.env` sem erro com `.env` de exemplo | `assert config.GROQ_API_KEY is not None` |

---

### Sprint 2

| ID | Critério | Método de Validação |
|----|----------|---------------------|
| AC2.1 | Estudante vê apenas cursos matriculados na Home | Query com user_id de estudante sem matrícula retorna lista vazia |
| AC2.2 | Badge de status exibe cor correta para DRAFT/GENERATING/COMPLETE | Verificar HTML/CSS dos badges |
| AC2.3 | Etapa 1: chamada à API Groq gera syllabus e salva módulos + lições no banco | Assert `len(modules) == num_modules` |
| AC2.4 | Etapa 2: streaming exibe chunks em tempo real sem erro de timeout | Mock stream retorna 3+ chunks |
| AC2.5 | `course_repo.create_course()` retorna ID válido | Assert `course_id > 0` |
| AC2.6 | Retry automático é acionado em status 429 da Groq | Mock 429 → assert 3 tentativas |

---

### Sprint 3

| ID | Critério | Método de Validação |
|----|----------|---------------------|
| AC3.1 | Estudante sem consentimento não acessa conteúdo | Assert redirect com `user_consents` vazio |
| AC3.2 | Consentimento salvo com timestamp em `user_consents` | Query retorna 1 row com `accepted_at` não nulo |
| AC3.3 | Sidebar lista todos os módulos e lições do curso | Assert len(sidebar_items) == total_lessons |
| AC3.4 | Lição marcada como completa aparece com badge ✅ na sidebar | Query `user_progress` retorna row |
| AC3.5 | Asset de imagem renderiza em grid de até 3 colunas | Assert max 3 colunas no layout |
| AC3.6 | Asset de documento gera botão de download | Assert `st.download_button` chamado |

---

### Sprint 4

| ID | Critério | Método de Validação |
|----|----------|---------------------|
| AC4.1 | Quiz exibe todas as questões do curso ativo | Assert `len(questions) == saved_count` |
| AC4.2 | Resposta correta exibe ✅ com explicação | Assert texto "Correct" presente |
| AC4.3 | Resposta errada exibe ❌ com resposta correta e explicação | Assert texto "Incorrect" + correct answer |
| AC4.4 | `quiz_service.generate_and_save_quiz()` salva N questões no banco | Assert `len(quiz_repo.get_by_course(id)) == N` |

---

### Sprint 5

| ID | Critério | Método de Validação |
|----|----------|---------------------|
| AC5.1 | Mensagem de chat é salva criptografada no banco | `assert stored_msg != original_msg` |
| AC5.2 | Histórico decriptado exibe texto original ao usuário | `assert decrypted == original_msg` |
| AC5.3 | Modo Curso injeta conteúdo do curso no system prompt | Assert nome do curso no prompt |
| AC5.4 | Palavra-chave "alcohol" aciona busca de cursos relacionados | Mock keyword + assert cursos no contexto |
| AC5.5 | Logout apaga `chatbot_history` do usuário | Query pós-logout retorna 0 rows |

---

### Sprint 6

| ID | Critério | Método de Validação |
|----|----------|---------------------|
| AC6.1 | General admin não vê outros admins na tabela de usuários | Assert nenhum `system_admin` na lista retornada |
| AC6.2 | Privacy Audit exige justificativa; sem ela botão fica desabilitado | Assert `st.button` disabled sem texto |
| AC6.3 | Acesso a Privacy Audit gera entrada em `audit_logs` | Query retorna evento `VIEW_SENSITIVE_DATA` |
| AC6.4 | Enrollments: matrícula cria row em `enrollments` e registra audit | Assert `enrollment` + `audit_log` criados |
| AC6.5 | Deleção de usuário aplica cascade (progresso, matrículas) | Assert tabelas relacionadas vazias após delete |

---

### Sprint 7

| ID | Critério | Método de Validação |
|----|----------|---------------------|
| AC7.1 | Tabela de progresso exibe `lições_concluídas/total` corretamente | Assert `2/8` com 2 progresses e 8 lições |
| AC7.2 | Instrutor vê apenas seus próprios cursos no dashboard | Assert cursos de outro instrutor ausentes |
| AC7.3 | Edição de metadados salva e registra audit log | Assert título atualizado + audit row |

---

### Sprint 8

| ID | Critério | Método de Validação |
|----|----------|---------------------|
| AC8.1 | Email de boas-vindas enviado ao criar usuário (mock SMTP) | Assert `smtplib.SMTP.sendmail` chamado |
| AC8.2 | Upload de imagem salva arquivo em `static/uploads/` com nome UUID | Assert `os.path.exists(path)` |
| AC8.3 | Etapa 3: clicar Skip redireciona para Content Player sem criar quiz | Assert `quiz_repo.get_by_course(id)` vazio |
| AC8.4 | Asset de vídeo renderiza player inline | Assert `st.video` chamado |

---

### Sprint 9

| ID | Critério | Método de Validação |
|----|----------|---------------------|
| AC9.1 | `pytest` passa com 0 falhas | `pytest --tb=short` exit code 0 |
| AC9.2 | `ruff check .` retorna 0 warnings | exit code 0 |
| AC9.3 | Nenhuma senha em texto plano em qualquer tabela | Query em `users.password_hash` → assert nenhum valor sem `$2b$` |
| AC9.4 | Conteúdo de `chatbot_history` é diferente do texto original (criptografado) | Assert stored != plaintext |

---

## 4. API Spec

> O projeto usa SQLAlchemy direto (sem REST API externa). "Endpoints" aqui são as funções públicas dos services e repositories.

---

### 4.1 Auth (`auth.py`)

| Função | Parâmetros | Retorno | Efeito |
|--------|------------|---------|--------|
| `login(email, password)` | `str, str` | `User \| None` | Cria `session_state`, audit log |
| `logout(user_id)` | `int` | `None` | Deleta `chatbot_history`, limpa sessão |
| `require_role(*roles)` | `str...` | `bool` | Redireciona se não autorizado |
| `get_current_user()` | — | `User \| None` | Lê `session_state` |

---

### 4.2 Course Repo (`repositories/course_repo.py`)

| Função | Parâmetros | Retorno |
|--------|------------|---------|
| `create_course(instructor_id, title, description)` | `int, str, str` | `Course` |
| `get_courses_by_role(user_id, role)` | `int, str` | `List[Course]` |
| `get_course_with_content(course_id)` | `int` | `Course` com módulos e lições |
| `update_course_status(course_id, status)` | `int, CourseStatus` | `None` |
| `delete_course(course_id)` | `int` | `None` (cascade) |
| `save_lesson_content(lesson_id, content)` | `int, str` | `None` |
| `add_lesson_asset(lesson_id, type, path, metadata)` | `int, str, str, dict` | `LessonAsset` |

---

### 4.3 User Repo (`repositories/user_repo.py`)

| Função | Parâmetros | Retorno |
|--------|------------|---------|
| `create_user(username, email, password, role)` | `str, str, str, str` | `User` |
| `get_user_by_email(email)` | `str` | `User \| None` |
| `update_user(user_id, **fields)` | `int, **kwargs` | `User` |
| `delete_user(user_id)` | `int` | `None` (cascade) |
| `mark_lesson_complete(user_id, lesson_id)` | `int, int` | `None` |
| `get_user_progress(user_id, course_id)` | `int, int` | `List[int]` (lesson_ids) |
| `log_audit(actor_id, action, target_id, details)` | `int, str, int, str` | `None` |
| `enroll_student(student_id, course_id)` | `int, int` | `Enrollment` |

---

### 4.4 AI Service (`services/ai_service.py`)

| Função | Parâmetros | Retorno |
|--------|------------|---------|
| `GroqProvider.generate(prompt, system)` | `str, str` | `str` |
| `GroqProvider.generate_stream(prompt, system)` | `str, str` | `Iterator[str]` |
| `resolve_api_key(user_id)` | `int` | `str` (chave resolvida) |

---

### 4.5 Chatbot Service (`services/chatbot_service.py`)

| Função | Parâmetros | Retorno |
|--------|------------|---------|
| `send_message(user_id, message, course_id?)` | `int, str, int?` | `Iterator[str]` |
| `get_history(user_id)` | `int` | `List[dict]` |
| `clear_history(user_id)` | `int` | `None` |
| `QuickChatService.send(user_id, lesson_id, message)` | `int, int, str` | `Iterator[str]` |

---

### 4.6 Payloads de Geração de Conteúdo

**Syllabus Input:**
```json
{
  "topic": "string",
  "num_modules": 4,
  "num_lessons": 3,
  "module_themes": "string (opcional)"
}
```

**Syllabus Output (salvo no banco):**
```json
{
  "course_id": 1,
  "title": "string",
  "description": "string",
  "modules": [
    {
      "title": "string",
      "order_index": 0,
      "lessons": [{"title": "string", "order_index": 0}]
    }
  ]
}
```

**Quiz Question (salvo em `quizzes`):**
```json
{
  "question": "string",
  "options_json": ["A", "B", "C", "D"],
  "correct_answer": "0",
  "explanation": "string"
}
```

---

## 5. Data Models

### Tabelas e Schemas

```python
# users
id: int (PK)
username: str (unique)
email: str (unique)
password_hash: str
role: enum [system_admin, general_admin, privacy_admin, instructor, student]
groq_api_key_encrypted: str | None
created_at: datetime

# audit_logs
id: int (PK)
actor_id: int (FK → users)
action: str  # LOGIN, LOGOUT, INSERT, UPDATE, DELETE, VIEW_SENSITIVE_DATA
target_id: int | None
details: str | None
timestamp: datetime

# courses
id: int (PK)
instructor_id: int (FK → users)
title: str
description: str
status: enum [DRAFT, GENERATING, COMPLETE]
tags: str | None
created_at: datetime

# modules
id: int (PK)
course_id: int (FK → courses, cascade delete)
title: str
order_index: int

# lessons
id: int (PK)
module_id: int (FK → modules, cascade delete)
title: str
content: str | None
order_index: int

# lesson_assets
id: int (PK)
lesson_id: int (FK → lessons, cascade delete)
asset_type: str  # image, video, document
file_path: str
label: str | None
alignment: str | None  # center, left, right
size_percent: int | None
position: str  # start, end

# quizzes
id: int (PK)
course_id: int (FK → courses, cascade delete)
question: str
options_json: str  # JSON array
correct_answer: str  # índice como string
explanation: str | None

# chatbot_history
id: int (PK)
user_id: int (FK → users, cascade delete)
message_content: str  # criptografado
bot_response: str  # criptografado
timestamp: datetime

# lesson_chat_messages
id: int (PK)
user_id: int (FK → users)
lesson_id: int (FK → lessons)
message: str
response: str
timestamp: datetime

# chat_messages (histórico de chat por curso, não criptografado)
id: int (PK)
user_id: int (FK → users)
course_id: int (FK → courses)
message: str
response: str
timestamp: datetime

# user_progress
id: int (PK)
user_id: int (FK → users, cascade delete)
lesson_id: int (FK → lessons, cascade delete)
completed_at: datetime
UNIQUE(user_id, lesson_id)

# enrollments
id: int (PK)
student_id: int (FK → users, cascade delete)
course_id: int (FK → courses, cascade delete)
enrolled_at: datetime
UNIQUE(student_id, course_id)

# user_consents
id: int (PK)
user_id: int (FK → users, cascade delete, unique)
accepted_at: datetime
```

### Relacionamentos
```
users (1) ──────── (N) audit_logs        [actor_id]
users (1) ──────── (N) user_progress
users (1) ──────── (N) enrollments
users (1) ──────── (N) courses           [instructor_id]
users (1) ──────── (N) chatbot_history
users (1) ──────── (1) user_consents

courses (1) ─────── (N) modules
courses (1) ─────── (N) quizzes
courses (1) ─────── (N) chat_messages
courses (1) ─────── (N) enrollments

modules (1) ─────── (N) lessons

lessons (1) ─────── (N) lesson_assets
lessons (1) ─────── (N) lesson_chat_messages
lessons (1) ─────── (N) user_progress
```

---

## 6. Stack

| Camada | Tecnologia | Versão mínima |
|--------|------------|---------------|
| UI | Streamlit | 1.32+ |
| ORM | SQLAlchemy | 2.0+ |
| Banco (dev) | SQLite | built-in |
| Banco (prod) | PostgreSQL | 15+ |
| LLM | Groq SDK (`groq`) | 0.9+ |
| Criptografia | `cryptography` (Fernet) | 42+ |
| Senhas | `bcrypt` | 4.0+ |
| Dados | `pandas` | 2.0+ |
| Env | `python-dotenv` | 1.0+ |
| Driver PG | `psycopg2-binary` | 2.9+ (opcional) |
| Lint | `ruff` | 0.4+ |
| Testes | `pytest` | 8.0+ |
| Python | Python | 3.11+ |

**Dependências do `requirements.txt`:**
```txt
streamlit>=1.32.0
sqlalchemy>=2.0.0
groq>=0.9.0
cryptography>=42.0.0
bcrypt>=4.0.0
pandas>=2.0.0
python-dotenv>=1.0.0
psycopg2-binary>=2.9.0
pytest>=8.0.0
ruff>=0.4.0
```

---

## 7. Coder Agent ID

| Sprint | Coder Agent | Evaluator Agent | Progress Agent |
|--------|-------------|-----------------|----------------|
| S1 | `coder-agent` | `evaluator-agent` | `progress-agent` |
| S2 | `coder-agent` | `evaluator-agent` | `progress-agent` |
| S3 | `coder-agent` | `evaluator-agent` | `progress-agent` |
| S4 | `coder-agent` | `evaluator-agent` | `progress-agent` |
| S5 | `coder-agent` | `evaluator-agent` | `progress-agent` |
| S6 | `coder-agent` | `evaluator-agent` | `progress-agent` |
| S7 | `coder-agent` | `evaluator-agent` | `progress-agent` |
| S8 | `coder-agent` | `evaluator-agent` | `progress-agent` |
| S9 | `coder-agent` | `evaluator-agent` | `progress-agent` |

---

## 8. File Structure

```
wocotm-academy/
│
├── app.py                          # Entry point Streamlit + navbar dinâmica
├── auth.py                         # Login, logout, require_role, deep linking
├── config.py                       # Variáveis de ambiente + parâmetros globais
├── requirements.txt
├── .env.example
│
├── db/
│   ├── __init__.py
│   ├── models.py                   # Todos os modelos SQLAlchemy (13 tabelas)
│   └── database.py                 # Engine, Session, init_db()
│
├── views/
│   ├── __init__.py
│   ├── home.py                     # Catálogo de cursos
│   ├── course_creator.py           # Wizard 3 etapas
│   ├── content_player.py           # Leitor de curso + sidebar + progresso
│   ├── quiz_view.py                # Avaliação
│   ├── chatbot_view.py             # Tutor AI
│   ├── instructor_dashboard.py     # Dashboard instrutor
│   └── admin_dashboard.py          # Painel admin
│
├── services/
│   ├── __init__.py
│   ├── ai_service.py               # GroqProvider (sync + stream + retry)
│   ├── chatbot_service.py          # ChatbotService + QuickChatService
│   ├── content_service.py          # Geração de conteúdo por lição
│   ├── syllabus_service.py         # Geração de syllabus
│   ├── quiz_service.py             # Geração de quizzes
│   ├── email_service.py            # SMTP STARTTLS + template HTML
│   ├── security_service.py         # EncryptionManager + hash bcrypt
│   └── privacy_service.py          # Consentimento LGPD
│
├── repositories/
│   ├── __init__.py
│   ├── user_repo.py                # CRUD usuários, audit, progresso, enrollments
│   ├── course_repo.py              # CRUD cursos, módulos, lições, assets
│   └── quiz_repo.py                # CRUD quizzes
│
├── utils/
│   ├── __init__.py
│   ├── prompts.py                  # Templates de system prompts
│   └── exporters.py                # Exportação de dados
│
├── static/
│   └── uploads/                    # Assets de mídia (UUID como nome)
│
└── tests/
    ├── __init__.py
    ├── test_auth.py
    ├── test_course_repo.py
    ├── test_user_repo.py
    ├── test_ai_service.py
    ├── test_chatbot_service.py
    ├── test_quiz_service.py
    └── conftest.py                 # Fixtures: DB em memória, mocks Groq
```

---

*SPEC.md gerado para o projeto WOCOTM Academy — antigravity*

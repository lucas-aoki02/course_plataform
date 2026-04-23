# 📄 Product Requirements Document (PRD)
## WOCOTM Academy — AI-Powered Course Platform

**Versão:** 1.0  
**Data:** Abril 2026  
**Status:** Em Produção  
**Stack:** Python · Streamlit · PostgreSQL/SQLite · Groq LLM (Llama 3.1 8B) · SQLAlchemy

---

## 1. Visão Geral do Produto

O **WOCOTM Academy** é uma plataforma de educação online alimentada por inteligência artificial, projetada para criação, distribuição e consumo de cursos no contexto de prevenção ao uso de álcool, drogas, saúde mental e bem-estar. A plataforma permite que instrutores criem cursos completos utilizando IA generativa (Groq/Llama) e que estudantes consumam o conteúdo em um ambiente seguro, com conformidade LGPD/GDPR.

### 1.1 Objetivos do Produto

- Democratizar a criação de conteúdo educacional com apoio de IA
- Garantir a segurança dos dados dos usuários (LGPD/GDPR)
- Fornecer um sistema de tutoria inteligente contextualizado ao curso
- Oferecer controle granular de acesso via sistema de papéis (RBAC)

---

## 2. Personas e Papéis (RBAC)

| Papel | Valor | Permissões |
|---|---|---|
| **System Admin** | `system_admin` | CRUD completo de todos os usuários incluindo outros admins. Acesso a todas as abas do painel incluindo logs de privacidade decriptados. |
| **General Admin** | `general_admin` | CRUD de instrutores e estudantes. Acesso a métricas agregadas. Não pode ver logs decriptados. |
| **Privacy Admin** | `privacy_admin` | CRUD de instrutores e estudantes. Acesso a logs de chat decriptados com justificativa obrigatória. |
| **Instructor** | `instructor` | Cria e gerencia seus próprios cursos. Vê progresso dos estudantes matriculados. Pode armazenar chave Groq pessoal. |
| **Student** | `student` | Visualiza apenas cursos nos quais está matriculado. Interage com o tutor IA. Marca lições como concluídas. |

---

## 3. Features do Produto

---

### 3.1 Autenticação e Controle de Sessão

**Módulo:** `auth.py`

#### 3.1.1 Login com E-mail e Senha
- Formulário centralizado com campos de e-mail e senha
- Autenticação via bcrypt (verificação de hash da senha)
- Sessão persistida no `st.session_state` durante toda a navegação
- Redirecionamento automático pós-login baseado no papel do usuário:
  - Admins → Admin Dashboard
  - Instrutores → Instructor Dashboard
  - Estudantes → Home (lista de cursos)
- Auditoria de login registrada na tabela `audit_logs`

#### 3.1.2 Logout com Limpeza de Dados
- Limpa o histórico do chatbot no banco de dados ao fazer logout
- Remove a sessão do `st.session_state`
- Redireciona para a tela de login
- Registra evento de logout no audit log

#### 3.1.3 Deep Linking via Query Params
- Suporte a `?course_id=<id>` na URL para acesso direto a um curso
- Se o usuário não estiver autenticado, o `course_id` fica pendente e é processado após o login
- Valida a existência do curso antes de redirecionar

#### 3.1.4 Proteção de Rotas por Papel
- Todas as rotas verificam o papel do usuário antes de renderizar
- Redirecionamento automático para usuários sem permissão
- Função utilitária `require_role(*roles)` para verificação rápida

---

### 3.2 Navegação (Navbar Dinâmica)

**Módulo:** `app.py`

A barra de navegação adapta os itens exibidos de acordo com o papel do usuário:

| Papel | Itens Visíveis |
|---|---|
| System / General / Privacy Admin | 🛡️ Admin · 👨‍🏫 Instructor · ✨ Create Course · 🏠 Home · 🤖 Tutor · [📖 Content] · [📝 Quiz] |
| Instructor | 👨‍🏫 My Dashboard · ✨ Create Course · 🏠 Home · 🤖 Tutor · [📖 Content] · [📝 Quiz] |
| Student | 🏠 Home · 🤖 Tutor · [📖 Content] · [📝 Quiz] |

> Items entre colchetes `[ ]` aparecem apenas quando há um curso ativo selecionado.

---

### 3.3 Home — Catálogo de Cursos

**Módulo:** `views/home.py`

#### 3.3.1 Listagem de Cursos Personalizada por Papel
- **Estudantes:** Veem apenas cursos nos quais estão matriculados
- **Instrutores:** Veem apenas cursos criados por eles
- **Admins:** Veem todos os cursos da plataforma

#### 3.3.2 Cards de Curso
- Exibe título, descrição (até 150 caracteres) e badge de status:
  - ⏳ **Draft** (âmbar) — rascunho
  - ⚙️ **Generating** (azul) — geração em progresso
  - ✅ **Complete** (verde) — curso publicado
- Botão **📖 View** → abre o Content Player
- Botão **🗑️ Delete** → visível apenas para não-estudantes

---

### 3.4 Criação de Cursos com IA (Wizard 3 etapas)

**Módulo:** `views/course_creator.py`  
**Dependências:** `services/syllabus_service.py`, `services/content_service.py`, `services/quiz_service.py`

#### 3.4.1 Etapa 1 — Definição do Tópico e Geração do Syllabus
- Campos de entrada:
  - **Tópico do Curso** (texto livre)
  - **Número de Módulos** (slider: 2–8, padrão 4)
  - **Lições por Módulo** (slider: 2–6, padrão 3)
  - **Temas dos Módulos** (campo opcional para guiar a IA)
- Clique em **✨ Generate Syllabus** → chama `generate_and_save_syllabus()`
- A IA (Groq/Llama 3.1 8B) gera título, descrição e estrutura (módulos + lições)
- Estrutura salva no banco de dados; wizard avança automaticamente para Etapa 2
- Badge visual "⚡ Powered by Groq (Llama 3 8B)"

#### 3.4.2 Etapa 2 — Edição Página a Página
- Navegação entre lições via dropdown
- Para cada lição:
  - **Slider de tamanho alvo** (0–50.000 caracteres, passo 500)
  - **⚡ Geração de conteúdo com streaming** via `generate_lesson_stream()` — exibição em tempo real
  - **🔄 Regenerate** — re-gera o conteúdo da lição preservando as outras
  - **Editor de texto** para revisão e edição manual do conteúdo gerado
  - **✅ Save Changes & Finalize Page** — salva no banco e avança para a próxima lição

#### 3.4.3 Gerenciador de Mídia por Lição
- Visualização de assets já inseridos com opção de exclusão
- Abas para inserção de novos assets:
  - **🖼️ Image (Upload):** PNG/JPG/JPEG; seleção de alinhamento (center/left/right), tamanho (25–100%) e posição (início/fim)
  - **📄 Document (PDF/Word):** Upload de PDF/DOC/DOCX com label personalizado
  - **🎥 Video (Upload):** Suporte a MP4/MOV/WEBM com alinhamento, tamanho e posição
- Todos os assets são salvos em `static/uploads/` com nome único (UUID)

#### 3.4.4 Etapa 3 — Geração de Quiz (Opcional)
- Botão **⚡ Generate AI Quiz** → chama `generate_and_save_quiz()` via Groq
- Botão **🚀 Skip - Go Direct to Course** para pular o quiz
- Após conclusão, redireciona para o Content Player do curso criado
- Estado do wizard resetado na conclusão

---

### 3.5 Content Player — Leitura de Cursos

**Módulo:** `views/content_player.py`

#### 3.5.1 Termo de Consentimento LGPD/GDPR (Estudantes)
- Modal de consentimento exibido na primeira vez que o estudante acessa qualquer curso
- Conteúdo do termo:
  - Privacidade dos dados (conversas criptografadas)
  - Uso ético (sem diagnósticos médicos)
  - Confidencialidade dos materiais
- Aceite registrado com timestamp no banco (`user_consents`)
- Acesso ao conteúdo bloqueado até aceitar os termos
- Botão "❌ Refuse and Return Home" disponível

#### 3.5.2 Navegação Lateral (Sidebar)
- Título do curso no topo
- Módulos e lições listados hierarquicamente
- Badge ✅ nas lições concluídas pelo estudante
- Clique em qualquer lição navega diretamente para ela
- Botão 🏠 Home no rodapé da sidebar

#### 3.5.3 Renderização de Conteúdo
- Título da lição como `h2`
- Suporte a Markdown completo (incluindo HTML embutido)
- Assets renderizados de acordo com posição (`start` ou `end`):
  - **Imagens:** Grid de até 3 colunas
  - **Vídeos:** Player inline de vídeo
  - **Documentos:** Botão de download (`⬇️ Download`)
- Suporte a imagens por URL e por caminho local

#### 3.5.4 Rastreamento de Progresso (Estudantes)
- Botão **✔️ Mark as Complete** ao final de cada lição
- Progresso salvo na tabela `user_progress`
- Estado persistido entre sessões

---

### 3.6 Quiz — Avaliação do Curso

**Módulo:** `views/quiz_view.py` · `services/quiz_service.py` · `repositories/quiz_repo.py`

- Exibe todas as questões do quiz do curso ativo
- Para cada questão:
  - Texto da pergunta em negrito
  - Opções de resposta via `st.radio`
  - Botão **Check Answer** por questão
  - Feedback imediato: ✅ Correto com explicação ou ❌ Errado com resposta correta e explicação
- Questões geradas pela IA com índice de resposta correta e explicação didática
- Formato de dados: `options_json` (lista JSON de strings), `correct_answer` (índice como string)

---

### 3.7 Tutor AI Inteligente (Chatbot)

**Módulo:** `views/chatbot_view.py` · `services/chatbot_service.py`

#### 3.7.1 Dois Modos de Operação

**Modo Curso** (quando `active_course_id` está definido):
- Sistema de prompt contextualizado com todo o conteúdo do curso ativo
- Responde dúvidas específicas sobre o material das lições
- Sugere outros cursos relacionados quando pertinente

**Modo Geral** (sem curso ativo):
- Sistema de prompt com catálogo completo de cursos da plataforma
- Indica cursos matriculados vs. disponíveis
- Recomendações de cursos baseadas em interesse demonstrado na conversa

#### 3.7.2 Persistência Criptografada do Histórico (LGPD)
- Todas as mensagens do usuário e respostas do bot são criptografadas com Fernet (AES-128) antes de salvar
- Tabela `chatbot_history` com `user_id`, `message_content` (enc.), `bot_response` (enc.)
- Histórico decriptado e exibido ao usuário em cada sessão
- **Histórico apagado do banco ao fazer logout** (garantia de privacidade)
- Limite configurável de mensagens no histórico (`MAX_CHAT_HISTORY = 20`)

#### 3.7.3 Detecção de Intenção e Recomendações
- Análise de palavras-chave na mensagem do usuário:
  `alcohol`, `prevention`, `health`, `mental`, `drug`, `addiction`, `family`, `recovery`, `smoke`, `tobacco`, `wellness`, `stress`, `trauma`
- Quando palavra-chave detectada, busca cursos relacionados no banco
- Contexto enriquecido é injetado no prompt do sistema: cursos matriculados vs. cursos disponíveis

#### 3.7.4 Streaming de Resposta
- Resposta do Groq exibida em tempo real (caractere a caractere) com indicador `▌`
- Fallback em caso de erro: mensagem de erro específica com dica de diagnóstico da chave API

#### 3.7.5 QuickChat por Lição (Serviço Complementar)
- `QuickChatService` para chat contextualizado ao conteúdo de uma lição específica
- Histórico salvo na tabela `lesson_chat_messages` (sem criptografia, sem limite de sessão)
- Útil para dúvidas pontuais durante a leitura de uma lição

---

### 3.8 Admin Dashboard

**Módulo:** `views/admin_dashboard.py`

#### 3.8.1 Aba: Usuários (👥)

**Visível para:** Todos os admins

- Tabela de usuários com: ID, Username, Email, Papel, indicador de chave Groq (✅/❌)
- **Filtro hierárquico:** Non-system admins só veem instrutores e estudantes (não podem ver outros admins)

**Criar Usuário:**
- Formulário com: username, email, senha, papel, chave Groq (opcional)
- System Admin pode criar qualquer papel; outros admins: apenas `instructor` e `student`
- Audit log automático ao criar

**Editar / Deletar Usuário:**
- Selectbox de usuários gerenciáveis (exclui o próprio admin logado)
- Edição de: username, email, senha, papel, chave Groq
- Deleção com cascade (progresso, matrículas, etc.)
- Audit log automático ao editar/deletar

#### 3.8.2 Aba: Privacy Audit (🔐) — System Admin e Privacy Admin

- Exige **justificativa textual** obrigatória antes de desbloquear
- Clique em **Unlock and View Logs** → registra acesso em audit log
- Exibe tabela: Timestamp, User ID, Mensagem decriptada, Resposta decriptada
- Acesso auditado automaticamente com a justificativa fornecida

#### 3.8.3 Aba: Privacy Metrics (📊) — General Admin

- Métricas agregadas e anonimizadas:
  - Total de interações com o chatbot
  - Número de estudantes únicos
- Sem acesso a conteúdo individual ou decriptado

#### 3.8.4 Aba: Audit Logs (📋)

**Visível para:** Todos os admins

- Tabela de todos os eventos do sistema: Timestamp, Actor (username), Ação, Detalhes
- Eventos registrados: `LOGIN`, `LOGOUT`, `INSERT`, `UPDATE`, `DELETE`, `VIEW_SENSITIVE_DATA`

#### 3.8.5 Aba: Enrollments (🔌)

**Visível para:** Todos os admins

- Interface para matricular estudantes em cursos
- Selectboxes para estudante e curso
- Botão ➕ Enroll com registro em audit log

---

### 3.9 Instructor Dashboard

**Módulo:** `views/instructor_dashboard.py`

#### 3.9.1 Aba: Student Progress (📊)

- Tabela de progresso por aluno por curso:
  - Aluno, E-mail, Curso, Lições concluídas (ex.: `2/8`), Percentual de progresso
- Instrutores veem apenas seus próprios cursos; Admins veem todos os cursos
- Calcula automaticamente baseado em `user_progress` e matrículas

#### 3.9.2 Aba: Courses Overview (📚)

- Cards expansíveis por curso com: título, status, sinopse, data de criação
- Botão **📖 Open Course** → abre o Content Player
- **Formulário de edição de metadados** por curso:
  - Título do curso
  - Sinopse
  - Tags (separadas por vírgula)
- Salva alterações com registro em audit log

---

### 3.10 Serviço de IA (Groq Integration)

**Módulo:** `services/ai_service.py`

#### 3.10.1 Resolução Dinâmica de Chave API
Ordem de prioridade:
1. Chave pessoal do instrutor (descriptografada do banco)
2. Chave de qualquer instrutor com chave disponível no banco (fallback)
3. Chave mestra do `.env` (`GROQ_API_KEY`)

#### 3.10.2 GroqProvider
- Model configurável via `.env` (`GROQ_MODEL`, default: `llama-3.1-8b-instant`)
- **Modo síncrono** (`generate`) → retorna string completa
- **Modo streaming** (`generate_stream`) → gera chunks para exibição em tempo real
- Retry automático em rate limit (429): até 3 tentativas com 2s de espera
- Mensagens de erro específicas para chave inválida (401) identificando a fonte (master ou instructor)

---

### 3.11 Segurança e Privacidade

**Módulo:** `services/security_service.py`

#### 3.11.1 Criptografia Simétrica (Fernet / AES-128-CBC)
- `EncryptionManager` como singleton global
- Chave configurada via `ENCRYPTION_KEY` no `.env`
- Usado para:
  - Criptografar/decriptografar mensagens do chatbot
  - Criptografar/decriptografar chaves Groq dos instrutores

#### 3.11.2 Hashing de Senhas (bcrypt)
- Senhas nunca armazenadas em texto plano
- Hash com salt gerado automaticamente
- Verificação via `verify_password()` sem revelar o hash

---

### 3.12 Serviço de E-mail

**Módulo:** `services/email_service.py`

- Envio de e-mail de boas-vindas ao criar novos usuários
- Protocolo: SMTP com STARTTLS (padrão Outlook, porta 587)
- Template HTML responsivo com:
  - Saudação personalizada com username
  - Credenciais de acesso (username, e-mail, senha temporária, papel)
  - Botão de acesso direto à plataforma (link configurável)
  - Rodapé com aviso de segurança e ano atual
- Falha silenciosa se credenciais de e-mail não configuradas

---

### 3.13 Banco de Dados e Modelos

**Módulo:** `db/models.py` · `db/database.py`

#### Tabelas Principais

| Tabela | Propósito |
|---|---|
| `users` | Usuários com papel, hash da senha, chave Groq criptografada |
| `audit_logs` | Registro de todas as ações do sistema |
| `user_progress` | Rastreamento de lições concluídas por estudante |
| `enrollments` | Matrículas de estudantes em cursos |
| `courses` | Metadados de cursos (título, descrição, status, tags, instructor_id) |
| `modules` | Módulos de um curso, ordenados por `order_index` |
| `lessons` | Lições de um módulo com conteúdo Markdown |
| `lesson_assets` | Assets de mídia (imagem/vídeo/documento) por lição |
| `quizzes` | Questões de quiz associadas a um curso |
| `chat_messages` | Histórico de chat a nível de curso (não encriptado) |
| `lesson_chat_messages` | Histórico de quick chat por lição |
| `chatbot_history` | Histórico de chat do tutor geral (encriptado, userId) |
| `user_consents` | Registro de aceite dos termos LGPD/GDPR |

#### Status de Curso (CourseStatus)
- `DRAFT` → criado, sem conteúdo gerado
- `GENERATING` → geração em progresso
- `COMPLETE` → conteúdo publicado e disponível

#### Suporte Multi-Banco
- **PostgreSQL** (produção) via `DATABASE_URL`
- **SQLite** (fallback local) — configuração padrão

---

## 4. Modelo de Dados — Diagrama de Relacionamentos

```
User (1) ─────────────── (N) AuditLog       [actor / target]
User (1) ─────────────── (N) UserProgress
User (1) ─────────────── (N) Enrollment
User (1) ─────────────── (N) Course          [instructor_id]
User (1) ─────────────── (N) ChatbotHistory  [criptografado]
User (1) ─────────────── (1) UserConsent

Course (1) ───────────── (N) Module          [order_index]
Course (1) ───────────── (N) Quiz
Course (1) ───────────── (N) ChatMessage
Course (1) ───────────── (N) Enrollment

Module (1) ───────────── (N) Lesson          [order_index]

Lesson (1) ───────────── (N) LessonAsset     [type, position]
Lesson (1) ───────────── (N) LessonChatMessage
Lesson (1) ───────────── (N) UserProgress
```

---

## 5. Configuração e Variáveis de Ambiente

**Módulo:** `config.py` (lê do `.env` na raiz do projeto)

| Variável | Padrão | Descrição |
|---|---|---|
| `GROQ_API_KEY` | _(obrigatório)_ | Chave mestra da API Groq |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Modelo LLM utilizado |
| `DATABASE_URL` | `sqlite:///course_platform.db` | URL do banco de dados |
| `ENCRYPTION_KEY` | _(obrigatório)_ | Chave Fernet para criptografia |
| `EMAIL_HOST` | `smtp-mail.outlook.com` | Servidor SMTP |
| `EMAIL_PORT` | `587` | Porta SMTP |
| `EMAIL_HOST_USER` | — | Usuário SMTP |
| `EMAIL_HOST_PASSWORD` | — | Senha SMTP |
| `EMAIL_FROM` | _(igual ao HOST_USER)_ | Endereço do remetente |
| `PLATFORM_URL` | `http://localhost:8501` | URL pública da plataforma (para e-mails) |
| `CONTENT_LANGUAGE` | `English (US)` | Idioma de geração de conteúdo |

### Parâmetros de Geração (hardcoded em config.py)

| Parâmetro | Valor |
|---|---|
| `DEFAULT_NUM_MODULES` | 4 |
| `DEFAULT_NUM_LESSONS` | 3 |
| `DEFAULT_NUM_QUESTIONS` | 5 |
| `MAX_CHAT_HISTORY` | 20 |

---

## 6. Arquitetura do Sistema

```
app.py (Streamlit Entry Point)
│
├── auth.py              — Autenticação, sessão, RBAC
│
├── views/
│   ├── home.py          — Catálogo de cursos
│   ├── course_creator.py — Wizard de criação de cursos
│   ├── content_player.py — Leitor de conteúdo
│   ├── quiz_view.py     — Avaliações
│   ├── chatbot_view.py  — Tutor AI
│   ├── instructor_dashboard.py — Dashboard do instrutor
│   └── admin_dashboard.py     — Painel administrativo
│
├── services/
│   ├── ai_service.py         — Integração Groq (LLM)
│   ├── chatbot_service.py    — Lógica do chatbot + QuickChat
│   ├── content_service.py    — Geração de conteúdo por lição
│   ├── syllabus_service.py   — Geração de syllabus
│   ├── quiz_service.py       — Geração de quizzes
│   ├── email_service.py      — Envio de e-mails SMTP
│   ├── security_service.py   — Criptografia + hashing
│   └── privacy_service.py    — Gerenciamento de consentimento LGPD
│
├── repositories/
│   ├── user_repo.py     — CRUD de usuários, auditoria, progresso
│   ├── course_repo.py   — CRUD de cursos, módulos, lições, assets
│   └── quiz_repo.py     — CRUD de quizzes
│
├── db/
│   ├── models.py        — Modelos SQLAlchemy (ORM)
│   └── database.py      — Engine, Session, init_db()
│
└── utils/
    ├── prompts.py       — Templates de system prompts para a IA
    └── exporters.py     — Utilitários de exportação
```

---

## 7. Fluxos Principais

### 7.1 Fluxo de Criação de Curso (Instrutor)

```
Login como Instructor
      ↓
Home → "➕ New Course"
      ↓
[Etapa 1] Inserir tópico, módulos, lições, temas opcionais
      ↓
Groq gera syllabus → salvo no banco
      ↓
[Etapa 2] Por lição: gerar conteúdo (streaming) → editar → salvar
          Inserir mídia (imagem/vídeo/documento) opcionalmente
      ↓
[Etapa 3] Gerar quiz via Groq (opcional) → ou pular
      ↓
Redireciona para Content Player do novo curso
```

### 7.2 Fluxo de Consumo de Curso (Estudante)

```
Login como Student
      ↓
Home → lista de cursos matriculados
      ↓
Clica "📖 View" em um curso
      ↓
[Primeiro acesso] Modal de Consentimento LGPD → Aceitar
      ↓
Content Player → navega pelas lições (sidebar)
      ↓
Ao final de cada lição: "✔️ Mark as Complete"
      ↓
Progresso salvo e badge ✅ exibido na sidebar
      ↓
[Opcional] Quiz → responde e recebe feedback imediato
[Opcional] Tutor AI → faz perguntas sobre o conteúdo
```

### 7.3 Fluxo de Gestão Admin

```
Login como Admin (qualquer tier)
      ↓
Admin Dashboard
├── Aba Usuários → CRUD de contas (escopo limitado por tier)
├── Aba Privacy → Audit (decriptado, com justificativa) ou Métricas (agregadas)
├── Aba Audit Logs → histórico de todas as ações
└── Aba Enrollments → matricular estudantes em cursos
```

---

## 8. Requisitos Não-Funcionais

| Requisito | Implementação |
|---|---|
| **Privacidade de dados (LGPD/GDPR)** | Criptografia AES-128 (Fernet) do histórico de chat; consentimento registrado com timestamp; acesso a logs com justificativa obrigatória |
| **Segurança de senhas** | Bcrypt com salt automático; senhas nunca armazenadas em texto plano |
| **Segurança de chaves API** | Chaves Groq dos instrutores criptografadas no banco |
| **Auditoria** | Todos os eventos críticos registrados em `audit_logs` (ator, ação, alvo, detalhes, timestamp) |
| **Resiliência da API** | Retry automático em rate limit (3 tentativas, 2s de espera) |
| **Performance de geração** | Streaming de respostas LLM para UX responsiva durante geração de conteúdo |
| **Portabilidade do banco** | Suporte nativo a PostgreSQL e SQLite via SQLAlchemy |
| **Privacidade em logout** | Histórico de chat deletado automaticamente ao fazer logout |

---

## 9. Dependências Principais

```txt
streamlit          — Framework de UI
sqlalchemy         — ORM para banco de dados
groq               — SDK oficial da API Groq
cryptography       — Criptografia Fernet
bcrypt             — Hashing de senhas
pandas             — Tabelas nos dashboards
python-dotenv      — Carregamento de variáveis de ambiente
psycopg2-binary    — Driver PostgreSQL (opcional)
```

---

*Documento gerado em 2026-04-16 — WOCOTM Academy v1.0*

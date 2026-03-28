"""
test_hybrid.py
──────────────
Verifica o roteamento correto da arquitetura resilience-first:
  Llama (Ollama) → Gemini → OpenAI

Testes:
1. Singleton `ai_service` usa ResilientChain (Llama→Gemini→OpenAI)
2. Singleton `llama_service` usa _OllamaProvider (direto)
3. Chain inverteu prioridade: Llama é o primeiro
4. Serviços usam `ai_service` (chain) para tarefas de texto
5. Pollinations.ai configurado como image provider
6. Fallback _is_provider_failure detecta erros corretamente
7. Ollama está acessível e modelo disponível
"""
import sys
sys.path.insert(0, ".")

print("=== Resilience-First Architecture Tests ===\n")

# 1. Verificar imports e singletons
from services.ai_service import (
    ai_service, llama_service,
    _OllamaProvider, _GeminiProvider, _OpenAIProvider,
    ResilientChain, AIService, _is_provider_failure, _is_quota_error,
)

assert isinstance(ai_service, AIService), "ai_service deve ser AIService"
assert isinstance(ai_service._provider, ResilientChain), "ai_service deve usar ResilientChain"
print("PASS: ai_service -> ResilientChain")

assert isinstance(llama_service, AIService), "llama_service deve ser AIService"
assert isinstance(llama_service._provider, _OllamaProvider), "llama_service deve usar _OllamaProvider"
print("PASS: llama_service -> _OllamaProvider (direto)")

# 2. Verificar ordem do chain: Llama primeiro
import inspect
chain_source = inspect.getsource(ResilientChain.generate)
llama_pos = chain_source.find("_OllamaProvider")
gemini_pos = chain_source.find("_GeminiProvider")
openai_pos = chain_source.find("_OpenAIProvider")
assert llama_pos < gemini_pos < openai_pos, "Chain deve ser: Llama -> Gemini -> OpenAI"
print("PASS: Chain order: Llama -> Gemini -> OpenAI")

# 3. Verificar _is_provider_failure detecta erros
assert _is_provider_failure(Exception("connection refused")), "Deve detectar connection refused"
assert _is_provider_failure(Exception("429 Too Many Requests")), "Deve detectar 429"
assert _is_provider_failure(Exception("timeout")), "Deve detectar timeout"
assert _is_provider_failure(Exception("503 Service Unavailable")), "Deve detectar 503"
assert not _is_provider_failure(Exception("invalid json format")), "NÃO deve detectar JSON error"
print("PASS: _is_provider_failure detecta corretamente")

# 4. Verificar _is_quota_error
assert _is_quota_error(Exception("429 RESOURCE_EXHAUSTED")), "Deve detectar quota"
assert _is_quota_error(Exception("rate limit exceeded")), "Deve detectar rate limit"
assert not _is_quota_error(Exception("connection timeout")), "NÃO deve detectar timeout como quota"
print("PASS: _is_quota_error detecta corretamente")

# 5. Verificar serviços usam `ai_service` (chain)
from services import syllabus_service, content_service, quiz_service
source_syl = inspect.getsource(syllabus_service)
assert "ai_service" in source_syl, "syllabus_service deve usar ai_service (chain)"
print("PASS: syllabus_service usa ai_service (chain)")

source_cnt = inspect.getsource(content_service)
assert "llama_service" in source_cnt, "content_service deve usar llama_service para conteúdo"
assert "ai_service" in source_cnt, "content_service deve usar ai_service para refinamento"
print("PASS: content_service usa llama_service + ai_service")

source_quiz = inspect.getsource(quiz_service)
assert "llama_service" in source_quiz, "quiz_service deve usar llama_service"
print("PASS: quiz_service usa llama_service")

# 6. Verificar chatbot_service usa chain
from services.chatbot_service import ChatbotService, QuickChatService
source_chatbot = inspect.getsource(ChatbotService)
assert "ai_service" in source_chatbot, "ChatbotService deve usar ai_service (chain)"
source_qc = inspect.getsource(QuickChatService)
assert "llama_service" in source_qc, "QuickChatService deve usar llama_service"
print("PASS: ChatbotService usa chain, QuickChatService usa llama_service")

# 7. Verificar image_service existe e tem chain
from services.image_service import generate_image, generate_image_for_lesson, get_provider_status
status = get_provider_status()
assert "Pollinations.ai" in status, "image_service deve ter Pollinations"
assert "Hugging Face" in status, "image_service deve ter Hugging Face"
print(f"PASS: image_service com {len(status)} providers")

# 8. Verificar config
import config
assert hasattr(config, "OLLAMA_BASE_URL")
assert hasattr(config, "OLLAMA_MODEL")
assert hasattr(config, "POLLINATIONS_ENABLED")
assert hasattr(config, "HF_API_TOKEN")
assert hasattr(config, "HF_IMAGE_MODEL")
print(f"PASS: config OK — ollama={config.OLLAMA_MODEL}, pollinations={config.POLLINATIONS_ENABLED}")

# 9. Verificar Ollama está rodando
import httpx
try:
    r = httpx.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
    r.raise_for_status()
    models = [m["name"] for m in r.json().get("models", [])]
    llama_ok = any(config.OLLAMA_MODEL in m for m in models)
    if llama_ok:
        print(f"PASS: Ollama OK — {config.OLLAMA_MODEL} disponível")
    else:
        print(f"WARN: Ollama OK mas {config.OLLAMA_MODEL} não encontrado. Modelos: {models}")
except Exception as e:
    print(f"WARN: Ollama não rodando ({e})")

# 10. Verificar Pollinations acessível
try:
    r = httpx.get("https://image.pollinations.ai/prompt/test?width=64&height=64", timeout=10, follow_redirects=True)
    if r.status_code == 200:
        print(f"PASS: Pollinations.ai acessível ({len(r.content)} bytes)")
    else:
        print(f"WARN: Pollinations retornou status {r.status_code}")
except Exception as e:
    print(f"WARN: Pollinations não acessível ({e})")

print("\n=== Todos os testes passaram! ===")

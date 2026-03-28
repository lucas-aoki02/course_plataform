"""
services/image_service.py
─────────────────────────
Geração de imagens com fallback automático:
  Pollinations.ai (primeira) → Hugging Face Inference API (segunda)

Função principal
────────────────
generate_image(prompt, filename) → str
    Gera imagem, salva em static/images/, retorna o caminho relativo
    para persistir no SQLite.

Uso
---
>>> path = generate_image("Diagrama de rede neural", "neural_net.png")
>>> print(path)  # "static/images/neural_net.png"
"""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
import urllib.parse

import config

logger = logging.getLogger(__name__)

# Pasta de destino
IMAGES_DIR = Path(__file__).parent.parent / "static" / "images"


class ImageGenerationError(Exception):
    """Raised when ALL image providers fail."""
    pass


def generate_image(prompt: str, filename: str = "") -> str:
    """
    Gera uma imagem a partir de um prompt de texto.

    Chain: Pollinations.ai → Hugging Face Inference API

    Args
    ----
    prompt   : Descrição textual da imagem a ser gerada.
    filename : Nome do arquivo (sem path). Se vazio, gera hash do prompt.

    Returns
    -------
    str : Caminho relativo do arquivo salvo (ex: "static/images/abc123.png").
          Pronto para salvar no SQLite.

    Raises
    ------
    ImageGenerationError : Se todos os providers falharem.
    """
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    if not filename:
        # Gerar nome único baseado no prompt
        hash_str = hashlib.md5(prompt.encode()).hexdigest()[:12]
        filename = f"img_{hash_str}_{int(time.time())}.png"

    filepath = IMAGES_DIR / filename
    errors: list[tuple[str, Exception]] = []

    # ── 1. Pollinations.ai (primeira tentativa) ──────────────────────────
    if config.POLLINATIONS_ENABLED:
        try:
            logger.info("[Image] Tentando Pollinations.ai...")
            image_bytes = _pollinations_generate(prompt)
            filepath.write_bytes(image_bytes)
            relative = f"static/images/{filename}"
            logger.info("[Image] Pollinations OK — %s (%d bytes)", relative, len(image_bytes))
            return relative
        except Exception as e:
            errors.append(("Pollinations.ai", e))
            logger.warning("[Image] Pollinations falhou: %s", e)

    # ── 2. Hugging Face Inference API (fallback) ─────────────────────────
    if config.HF_API_TOKEN:
        try:
            logger.info("[Image] Tentando Hugging Face (fallback)...")
            image_bytes = _huggingface_generate(prompt)
            filepath.write_bytes(image_bytes)
            relative = f"static/images/{filename}"
            logger.info("[Image] HuggingFace OK — %s (%d bytes)", relative, len(image_bytes))
            return relative
        except Exception as e:
            errors.append(("Hugging Face", e))
            logger.warning("[Image] Hugging Face falhou: %s", e)

    # ── Todos falharam ───────────────────────────────────────────────────
    error_summary = "; ".join(f"{name}: {err}" for name, err in errors)
    raise ImageGenerationError(
        f"Todos os providers de imagem falharam: {error_summary}"
    )


def generate_image_for_lesson(lesson_title: str, lesson_content: str) -> str:
    """
    Gera uma imagem ilustrativa para uma lição do curso.

    Constrói um prompt de imagem a partir do título e conteúdo da lição.

    Args
    ----
    lesson_title   : Título da lição.
    lesson_content : Conteúdo markdown da lição.

    Returns
    -------
    str : Caminho relativo da imagem salva.
    """
    # Extrair primeiro parágrafo como contexto
    content_preview = lesson_content[:300].replace("#", "").replace("*", "").strip()

    image_prompt = (
        f"Educational illustration for a lesson titled '{lesson_title}'. "
        f"Clean, professional, modern infographic style. "
        f"Topic: {content_preview}. "
        f"No text in the image, visual metaphor only."
    )

    # Nome do arquivo baseado no título
    slug = "".join(c if c.isalnum() else "_" for c in lesson_title.lower())[:40]
    filename = f"lesson_{slug}_{int(time.time())}.png"

    return generate_image(image_prompt, filename)


# ── Provider: Pollinations.ai ─────────────────────────────────────────────────

def _pollinations_generate(prompt: str) -> bytes:
    """
    Gera imagem via Pollinations.ai (gen.pollinations.ai).

    Endpoint: GET https://gen.pollinations.ai/image/{prompt}
    Aceita API key via query param `key` ou header `Authorization`.
    """
    import httpx

    encoded = urllib.parse.quote(prompt)

    # Endpoint unificado do Pollinations (2026)
    url = f"https://gen.pollinations.ai/image/{encoded}"

    params = {
        "width": str(config.POLLINATIONS_WIDTH),
        "height": str(config.POLLINATIONS_HEIGHT),
        "nologo": "true",
        "seed": str(int(time.time()) % 100000),
    }
    if config.POLLINATIONS_MODEL:
        params["model"] = config.POLLINATIONS_MODEL

    headers = {}
    if config.POLLINATIONS_API_KEY:
        headers["Authorization"] = f"Bearer {config.POLLINATIONS_API_KEY}"

    with httpx.Client(timeout=120) as client:
        response = client.get(
            url,
            params=params,
            headers=headers,
            follow_redirects=True,
        )

        # Tratar erros
        if response.status_code == 401:
            raise ImageGenerationError(
                "Pollinations requer API key. Gere em https://enter.pollinations.ai "
                "e adicione POLLINATIONS_API_KEY no .env"
            )

        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "image" not in content_type:
            body = response.text[:300]
            raise ImageGenerationError(
                f"Pollinations retornou não-imagem (status {response.status_code}): {body}"
            )

        data = response.content
        if len(data) < 500:
            raise ImageGenerationError(
                f"Pollinations retornou imagem muito pequena ({len(data)} bytes)"
            )

        return data


# ── Provider: Hugging Face Inference API ──────────────────────────────────────

def _huggingface_generate(prompt: str) -> bytes:
    """
    Gera imagem via Hugging Face Inference API (router.huggingface.co).

    Endpoint: POST https://router.huggingface.co/hf-inference/models/{model}
    Header: Authorization: Bearer {token}
    Body: {"inputs": prompt}

    Se o modelo estiver carregando (503), espera e tenta novamente.
    """
    import httpx

    # Novo endpoint do HF (2026) — api-inference foi descontinuado
    url = f"https://router.huggingface.co/hf-inference/models/{config.HF_IMAGE_MODEL}"
    headers = {
        "Authorization": f"Bearer {config.HF_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"inputs": prompt}

    with httpx.Client(timeout=config.HF_TIMEOUT) as client:
        response = client.post(url, json=payload, headers=headers)

        # Modelo carregando — esperar e tentar de novo
        if response.status_code == 503:
            wait_time = response.json().get("estimated_time", 30)
            logger.info("[Image] HF modelo carregando, esperando %.0fs...", wait_time)
            time.sleep(min(wait_time, 60))
            response = client.post(url, json=payload, headers=headers)

        # Erro de autenticação
        if response.status_code == 401:
            raise ImageGenerationError(
                "Hugging Face token inválido. Verifique HF_API_TOKEN no .env"
            )

        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "image" not in content_type:
            error_msg = response.text[:300]
            raise ImageGenerationError(f"Hugging Face retornou erro: {error_msg}")

        data = response.content
        if len(data) < 500:
            raise ImageGenerationError(
                f"Hugging Face retornou imagem muito pequena ({len(data)} bytes)"
            )

        return data


# ── Status / Diagnóstico ──────────────────────────────────────────────────────

def get_provider_status() -> dict:
    """
    Retorna o status de cada provider de imagem (para exibir na UI).

    Returns
    -------
    dict : nome_do_provider → {"available": bool, "details": str}
    """
    return {
        "Pollinations.ai": {
            "available": config.POLLINATIONS_ENABLED,
            "has_key": bool(config.POLLINATIONS_API_KEY),
            "details": (
                "API key configurada"
                if config.POLLINATIONS_API_KEY
                else "Sem key — adicione POLLINATIONS_API_KEY no .env"
            ),
            "model": config.POLLINATIONS_MODEL,
            "resolution": f"{config.POLLINATIONS_WIDTH}x{config.POLLINATIONS_HEIGHT}",
        },
        "Hugging Face": {
            "available": bool(config.HF_API_TOKEN),
            "has_key": bool(config.HF_API_TOKEN),
            "details": (
                "Token configurado"
                if config.HF_API_TOKEN
                else "Sem token — adicione HF_API_TOKEN no .env"
            ),
            "model": config.HF_IMAGE_MODEL,
        },
    }

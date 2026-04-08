"""
AI Answering Module
Supports Groq (Llama 3) and Google Gemini APIs to answer detected questions.
Auto-detects which provider to use based on the API key format.
Uses 'requests' library to avoid Cloudflare blocking with urllib.
"""

import json
import requests


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def detect_provider(api_key: str) -> str:
    """Auto-detect API provider from key format."""
    if api_key.startswith("gsk_"):
        return "groq"
    elif api_key.startswith("AIza"):
        return "gemini"
    else:
        return "groq"


def _build_prompt(question: str, options: list) -> str:
    """Build an optimized prompt for the AI depending on question type."""
    if options:
        options_text = "\n".join(options)
        return (
            f"Ejerces el rol del mejor experto analítico del mundo resolviendo preguntas complejas de tipo Quiz o Test.\n"
            f"Tu ÚNICO objetivo es la PRECISIÓN ABSOLUTA (100% de exactitud). No importa cuánto texto necesites generar para estar seguro, prioriza la corrección por sobre cualquier otra cosa.\n\n"
            f"=== CONTEXTO DETECTADO EN PANTALLA ===\n{question}\n\n"
            f"=== OPCIONES (MULTIPLE CHOICE) ===\n{options_text}\n\n"
            f"INSTRUCCIONES CRÍTICAS DE RAZONAMIENTO:\n"
            f"1. Piensa paso a paso bajo la etiqueta 'RAZONAMIENTO:'.\n"
            f"2. Primero, analiza qué está preguntando exactamente el enunciado. Identifica trampas, palabras clave (ej. 'NO', 'EXCEPTO', 'SIEMPRE').\n"
            f"3. Revisa cada una de las opciones propuestas una por una. Explica por qué es correcta o incorrecta basándote en hechos irrefutables.\n"
            f"4. Haz una doble verificación interna antes de concluir (¿estoy absolutamente seguro?).\n"
            f"5. Finalmente, bajo la etiqueta 'RESPUESTA:', escribe ÚNICA Y EXCLUSIVAMENTE el texto literal de la opción que has deducido como correcta (ej. 'B 1986' si la opción era 'B 1986'). Sin añadir puntos ni comillas si no están en la opción.\n\n"
            f"EJEMPLO ESPERADO:\n"
            f"RAZONAMIENTO: La pregunta pide identificar la excepción. Analisis opción por opción... En conclusión, estoy 100% seguro de mi decisión.\n"
            f"RESPUESTA: C El metabolismo celular"
        )
    else:
        return (
            f"Ejerces el rol del mejor experto analítico del mundo.\n"
            f"Tu ÚNICO objetivo es la PRECISIÓN ABSOLUTA. Analiza en profundidad la pregunta antes de responder.\n\n"
            f"=== CONTEXTO DETECTADO EN PANTALLA ===\n{question}\n\n"
            f"INSTRUCCIONES CRÍTICAS:\n"
            f"1. Piensa lenta y meticulosamente bajo 'RAZONAMIENTO:'. Reflexiona sobre los matices de lo que se pregunta, evalúa posibles interpretaciones erróneas y aclara cualquier ambigüedad.\n"
            f"2. Formato EXACTO a usar al final:\n"
            f"   RAZONAMIENTO: [tu análisis destructivo paso a paso de por qué esta será la respuesta irrefutable]\n"
            f"   RESPUESTA: [tu conclusión final directa, concisa y 100% precisa en 1 o 2 sentencias]"
        )


def _call_groq(prompt: str, api_key: str) -> str:
    """Call Groq API and return raw text response."""
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Eres un asistente experto de máxima precisión. Analiza meticulosamente cada detalle antes de concluir. Responde siempre en español."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 2048,
    }

    response = requests.post(
        GROQ_API_URL,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        timeout=15
    )
    response.raise_for_status()
    result = response.json()
    return result["choices"][0]["message"]["content"]


def _call_gemini(prompt: str, api_key: str) -> str:
    """Call Gemini API and return raw text response."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 1000,
        }
    }

    url = f"{GEMINI_API_URL}?key={api_key}"
    response = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=15
    )
    response.raise_for_status()
    result = response.json()
    return result["candidates"][0]["content"]["parts"][0]["text"]


def _parse_response(raw_text: str) -> tuple:
    """Parse the AI response to extract answer and explanation."""
    import re
    respuesta = None
    explicacion = None

    # Limpiar formato markdown (negritas) 
    raw_clean = raw_text.replace("**", "")

    # Extraer razonamiento (todo entre RAZONAMIENTO: y RESPUESTA:)
    raz_match = re.search(r"RAZONAMIENTO:\s*(.*?)(?=RESPUESTA:|$)", raw_clean, re.DOTALL | re.IGNORECASE)
    if raz_match:
        explicacion = raz_match.group(1).strip()

    # Extraer respuesta (todo después de RESPUESTA:)
    ans_match = re.search(r"RESPUESTA:\s*(.*)", raw_clean, re.IGNORECASE)
    if ans_match:
        respuesta = ans_match.group(1).strip()

    # Fallback si no siguió el formato
    if not respuesta:
        respuesta = raw_text.strip()

    return respuesta, explicacion


def ask_ai(question: str, options: list, api_key: str) -> dict:
    """
    Send a question to the AI and return the answer.
    Auto-detects provider (Groq or Gemini) from the API key.
    """
    if not question:
        return {
            "respuesta": None,
            "explicacion": None,
            "raw_response": None,
            "provider": None,
            "error": "No hay pregunta para responder."
        }

    provider = detect_provider(api_key)
    prompt = _build_prompt(question, options)

    try:
        if provider == "groq":
            raw_text = _call_groq(prompt, api_key)
        else:
            raw_text = _call_gemini(prompt, api_key)

        respuesta, explicacion = _parse_response(raw_text)

        return {
            "respuesta": respuesta,
            "explicacion": explicacion,
            "raw_response": raw_text.strip(),
            "provider": provider,
            "error": None
        }

    except requests.exceptions.HTTPError as e:
        error_body = ""
        if e.response is not None:
            error_body = e.response.text[:200]
        return {
            "respuesta": None, "explicacion": None, "raw_response": None,
            "provider": provider,
            "error": f"HTTP {e.response.status_code if e.response else '?'}: {error_body}"
        }
    except requests.exceptions.ConnectionError:
        return {
            "respuesta": None, "explicacion": None, "raw_response": None,
            "provider": provider, "error": "Error de conexión. Verifica tu internet."
        }
    except requests.exceptions.Timeout:
        return {
            "respuesta": None, "explicacion": None, "raw_response": None,
            "provider": provider, "error": "Timeout: la API tardó demasiado."
        }
    except Exception as e:
        return {
            "respuesta": None, "explicacion": None, "raw_response": None,
            "provider": provider, "error": f"{type(e).__name__}: {str(e)}"
        }


# Backward compatibility
def ask_gemini(question, options, api_key):
    return ask_ai(question, options, api_key)


if __name__ == "__main__":
    API_KEY = "TU_API_KEY_AQUI"

    provider = detect_provider(API_KEY)
    print(f"Provider detectado: {provider}\n")

    print("=== Test: Multiple Choice ===")
    result = ask_ai(
        "¿Cuál es la capital de Francia?",
        ["a) Madrid", "b) París", "c) Roma", "d) Berlín"],
        API_KEY
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n=== Test: Open Question ===")
    result = ask_ai(
        "¿En qué año llegó el hombre a la Luna?",
        [],
        API_KEY
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

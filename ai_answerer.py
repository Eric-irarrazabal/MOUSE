"""
AI Answering Module — Two-Pass Verification System
Supports Groq (Llama 3) and Google Gemini APIs to answer detected questions.
Auto-detects which provider to use based on the API key format.
Uses two-pass verification for maximum accuracy and confidence scoring.
"""

import json
import re
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


def _build_prompt_pass1(question: str, options: list) -> str:
    """Build Pass 1 prompt: deep per-option analysis with confidence."""
    if options:
        options_text = "\n".join(options)
        return (
            f"Eres un experto absoluto resolviendo preguntas de tipo Quiz/Test. "
            f"Tu objetivo es lograr precision PERFECTA.\n\n"
            f"=== CONTEXTO DETECTADO EN PANTALLA ===\n{question}\n\n"
            f"=== OPCIONES ===\n{options_text}\n\n"
            f"INSTRUCCIONES (SIGUE ESTE PROCESO EXACTO):\n"
            f"1. Lee el contexto completo e identifica la VERDADERA pregunta ignorando ruido de OCR.\n"
            f"2. Analiza CADA opcion individualmente:\n"
            f"   - Para cada una, explica con argumentos solidos por que ES o NO ES la correcta.\n"
            f"   - Busca trampas, ambiguedades y matices.\n"
            f"3. Despues de analizar TODAS, elige la respuesta correcta con argumentacion definitiva.\n"
            f"4. Asigna un nivel de confianza (0-100) basado en cuan seguro estas de tu respuesta.\n\n"
            f"FORMATO EXACTO DE RESPUESTA (respeta las etiquetas):\n"
            f"ANALISIS:\n"
            f"- Opcion [letra/texto]: [por que si/no es correcta]\n"
            f"- Opcion [letra/texto]: [por que si/no es correcta]\n"
            f"...\n"
            f"RAZONAMIENTO: [conclusion final basada en el analisis completo]\n"
            f"RESPUESTA: [texto EXACTO de la opcion elegida, copiado tal cual aparece arriba]\n"
            f"CONFIANZA: [numero entero 0-100]"
        )
    else:
        return (
            f"Eres un experto absoluto analizando y respondiendo preguntas. "
            f"Tu objetivo es lograr precision PERFECTA.\n\n"
            f"=== CONTEXTO DETECTADO EN PANTALLA ===\n{question}\n\n"
            f"INSTRUCCIONES:\n"
            f"1. Lee el contexto completo e identifica la VERDADERA pregunta ignorando ruido de OCR.\n"
            f"2. Piensa paso a paso y analiza cuidadosamente.\n"
            f"3. Busca trampas argumentativas antes de concluir.\n\n"
            f"FORMATO EXACTO:\n"
            f"RAZONAMIENTO: [tu analisis detallado]\n"
            f"RESPUESTA: [tu conclusion final directa en 1-2 sentencias]\n"
            f"CONFIANZA: [numero entero 0-100]"
        )


def _build_prompt_pass2(question: str, options: list, previous_answer: str) -> str:
    """Build Pass 2 prompt: independent verification ignoring previous answer."""
    if options:
        options_text = "\n".join(options)
        return (
            f"Eres un verificador experto independiente. "
            f"Tu tarea es resolver esta pregunta DESDE CERO con maxima precision.\n\n"
            f"=== PREGUNTA ===\n{question}\n\n"
            f"=== OPCIONES ===\n{options_text}\n\n"
            f"INSTRUCCIONES CRITICAS:\n"
            f"1. IGNORA cualquier respuesta previa. Analiza completamente desde cero.\n"
            f"2. Para CADA opcion, evalua independientemente si es correcta o incorrecta.\n"
            f"3. Verifica tu razonamiento buscando contraejemplos o errores logicos.\n"
            f"4. Solo cuando estes seguro, indica tu respuesta final.\n\n"
            f"FORMATO EXACTO:\n"
            f"RAZONAMIENTO: [tu analisis independiente y completo]\n"
            f"RESPUESTA: [texto EXACTO de la opcion elegida]\n"
            f"CONFIANZA: [numero entero 0-100]"
        )
    else:
        return (
            f"Eres un verificador experto. Resuelve esta pregunta desde cero.\n\n"
            f"=== PREGUNTA ===\n{question}\n\n"
            f"FORMATO EXACTO:\n"
            f"RAZONAMIENTO: [tu analisis completo]\n"
            f"RESPUESTA: [tu conclusion final]\n"
            f"CONFIANZA: [numero entero 0-100]"
        )


SYSTEM_PROMPT = (
    "Eres un asistente experto de MAXIMA precision. "
    "Analiza meticulosamente cada detalle antes de concluir. "
    "NUNCA respondas apresuradamente. Piensa profundamente. "
    "Responde siempre en espanol."
)


def _call_groq(prompt: str, api_key: str) -> str:
    """Call Groq API and return raw text response."""
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 1024,
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
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 1024,
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


def _call_provider(prompt: str, api_key: str, provider: str) -> str:
    """Route to the correct provider."""
    if provider == "groq":
        return _call_groq(prompt, api_key)
    else:
        return _call_gemini(prompt, api_key)


def _parse_response(raw_text: str) -> dict:
    """Parse AI response to extract answer, explanation, and confidence."""
    raw_clean = raw_text.replace("**", "")

    explicacion = None
    respuesta = None
    confianza = 50  # Default if not parseable

    # Extract RAZONAMIENTO
    raz_match = re.search(
        r"RAZONAMIENTO:\s*(.*?)(?=RESPUESTA:|$)", raw_clean, re.DOTALL | re.IGNORECASE
    )
    if raz_match:
        explicacion = raz_match.group(1).strip()

    # Extract RESPUESTA
    ans_match = re.search(
        r"RESPUESTA:\s*(.*?)(?=CONFIANZA:|$)", raw_clean, re.DOTALL | re.IGNORECASE
    )
    if ans_match:
        respuesta = ans_match.group(1).strip()
    else:
        # Fallback: try without CONFIANZA boundary
        ans_match2 = re.search(r"RESPUESTA:\s*(.*)", raw_clean, re.IGNORECASE)
        if ans_match2:
            respuesta = ans_match2.group(1).strip()

    # Extract CONFIANZA
    conf_match = re.search(r"CONFIANZA:\s*(\d{1,3})", raw_clean, re.IGNORECASE)
    if conf_match:
        confianza = int(conf_match.group(1))
        confianza = max(0, min(100, confianza))

    # Fallback if no format followed
    if not respuesta:
        respuesta = raw_text.strip()

    return {
        "respuesta": respuesta,
        "explicacion": explicacion,
        "confianza": confianza
    }


def _normalize(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r'[^a-z0-9\s]', '', text.lower()).strip()


def match_to_option_index(answer: str, options: list) -> int:
    """
    Match an AI answer to the best option index.
    Returns the index or None if no confident match.
    """
    if not answer or not options:
        return None

    answer_clean = answer.strip()
    answer_upper = answer_clean.upper()
    answer_norm = _normalize(answer_clean)

    # 1. Exact match (case-insensitive, stripped)
    for i, opt in enumerate(options):
        opt_text = opt.strip() if isinstance(opt, str) else opt
        if _normalize(opt_text) == answer_norm:
            return i

    # 2. Answer contains option text or vice versa (case-insensitive)
    for i, opt in enumerate(options):
        opt_text = opt.strip() if isinstance(opt, str) else opt
        opt_upper = opt_text.upper()
        if opt_upper in answer_upper or answer_upper in opt_upper:
            return i

    # 3. Letter/number prefix match (e.g., "B" or "B)" or "2")
    letter_match = re.match(r'^([A-Za-z])\s*[).\-]?\s', answer_clean)
    if letter_match:
        target_letter = letter_match.group(1).upper()
        for i, opt in enumerate(options):
            opt_text = opt.strip() if isinstance(opt, str) else opt
            opt_letter_match = re.match(r'^([A-Za-z])\s*[).\-]?\s', opt_text)
            if opt_letter_match and opt_letter_match.group(1).upper() == target_letter:
                return i

    # 4. Word overlap > 60%
    answer_words = set(answer_norm.split())
    if answer_words:
        best_idx = None
        best_ratio = 0.0
        for i, opt in enumerate(options):
            opt_text = opt.strip() if isinstance(opt, str) else opt
            opt_words = set(_normalize(opt_text).split())
            if not opt_words:
                continue
            common = answer_words & opt_words
            ratio = len(common) / max(len(answer_words), len(opt_words))
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = i
        if best_ratio >= 0.6 and best_idx is not None:
            return best_idx

    # 5. Fallback: first 3 chars
    for i, opt in enumerate(options):
        opt_text = opt.strip() if isinstance(opt, str) else opt
        if opt_text[:3].upper() in answer_upper:
            return i

    return None


def _answers_match(answer1: str, answer2: str, options: list) -> bool:
    """Check if two answers refer to the same option."""
    idx1 = match_to_option_index(answer1, options)
    idx2 = match_to_option_index(answer2, options)
    if idx1 is not None and idx2 is not None:
        return idx1 == idx2
    # Fallback: direct normalized comparison
    return _normalize(answer1) == _normalize(answer2)


def ask_ai(question: str, options: list, api_key: str) -> dict:
    """
    Two-pass AI analysis for maximum accuracy.
    Pass 1: Deep per-option analysis.
    Pass 2 (if needed): Independent verification.
    """
    if not question:
        return {
            "respuesta": None, "explicacion": None, "confianza": 0,
            "raw_response": None, "provider": None, "pass_count": 0,
            "error": "No hay pregunta para responder."
        }

    provider = detect_provider(api_key)

    try:
        # ═══ PASS 1: Deep analysis ═══
        prompt1 = _build_prompt_pass1(question, options)
        raw1 = _call_provider(prompt1, api_key, provider)
        result1 = _parse_response(raw1)

        print(f"  [PASS 1] Respuesta: {result1['respuesta'][:80]}...")
        print(f"  [PASS 1] Confianza: {result1['confianza']}%")

        # Fast path: very high confidence on first pass
        if result1["confianza"] >= 95:
            print(f"  [FAST PATH] Confianza >= 95%, aceptando sin verificacion.")
            return {
                "respuesta": result1["respuesta"],
                "explicacion": result1["explicacion"],
                "confianza": result1["confianza"],
                "raw_response": raw1.strip(),
                "provider": provider,
                "pass_count": 1,
                "error": None
            }

        # ═══ PASS 2: Independent verification ═══
        print(f"  [PASS 2] Verificando independientemente...")
        prompt2 = _build_prompt_pass2(question, options, result1["respuesta"])
        raw2 = _call_provider(prompt2, api_key, provider)
        result2 = _parse_response(raw2)

        print(f"  [PASS 2] Respuesta: {result2['respuesta'][:80]}...")
        print(f"  [PASS 2] Confianza: {result2['confianza']}%")

        combined_raw = raw1.strip() + "\n\n--- VERIFICACION ---\n\n" + raw2.strip()

        # Agreement check
        if options and _answers_match(result1["respuesta"], result2["respuesta"], options):
            # Both passes agree — boost confidence
            final_confidence = min(100, max(result1["confianza"], result2["confianza"]) + 10)
            print(f"  [ACUERDO] Ambas pasadas coinciden. Confianza final: {final_confidence}%")
            # Use the explanation from pass 1 (more detailed)
            return {
                "respuesta": result1["respuesta"],
                "explicacion": result1["explicacion"],
                "confianza": final_confidence,
                "raw_response": combined_raw,
                "provider": provider,
                "pass_count": 2,
                "error": None
            }
        elif not options:
            # Open-ended question: use pass 1 result with averaged confidence
            final_confidence = (result1["confianza"] + result2["confianza"]) // 2
            return {
                "respuesta": result1["respuesta"],
                "explicacion": result1["explicacion"],
                "confianza": final_confidence,
                "raw_response": combined_raw,
                "provider": provider,
                "pass_count": 2,
                "error": None
            }
        else:
            # Disagreement — use higher confidence answer, penalize
            print(f"  [DESACUERDO] Las pasadas difieren.")
            if result1["confianza"] >= result2["confianza"]:
                winner = result1
            else:
                winner = result2
            final_confidence = max(30, winner["confianza"] - 20)
            print(f"  [DESACUERDO] Usando respuesta con mayor confianza. Final: {final_confidence}%")
            return {
                "respuesta": winner["respuesta"],
                "explicacion": winner["explicacion"],
                "confianza": final_confidence,
                "raw_response": combined_raw,
                "provider": provider,
                "pass_count": 2,
                "error": None
            }

    except requests.exceptions.HTTPError as e:
        error_body = ""
        if e.response is not None:
            error_body = e.response.text[:200]
        return {
            "respuesta": None, "explicacion": None, "confianza": 0,
            "raw_response": None, "provider": provider, "pass_count": 0,
            "error": f"HTTP {e.response.status_code if e.response else '?'}: {error_body}"
        }
    except requests.exceptions.ConnectionError:
        return {
            "respuesta": None, "explicacion": None, "confianza": 0,
            "raw_response": None, "provider": provider, "pass_count": 0,
            "error": "Error de conexion. Verifica tu internet."
        }
    except requests.exceptions.Timeout:
        return {
            "respuesta": None, "explicacion": None, "confianza": 0,
            "raw_response": None, "provider": provider, "pass_count": 0,
            "error": "Timeout: la API tardo demasiado."
        }
    except Exception as e:
        return {
            "respuesta": None, "explicacion": None, "confianza": 0,
            "raw_response": None, "provider": provider, "pass_count": 0,
            "error": f"{type(e).__name__}: {str(e)}"
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
        "¿Cual es la capital de Francia?",
        ["a) Madrid", "b) Paris", "c) Roma", "d) Berlin"],
        API_KEY
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n=== Test: Open Question ===")
    result = ask_ai(
        "¿En que ano llego el hombre a la Luna?",
        [],
        API_KEY
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

import requests
from typing import Tuple, Dict, Any
from django.conf import settings

VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


def verify_recaptcha(token: str, expected_action: str = "login", remoteip: str | None = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Verifica un token de reCAPTCHA v3 contra la API de Google.

    Devuelve: (is_valid, payload_json)
      - is_valid: True si success==True, action coincide y score >= umbral
      - payload_json: respuesta completa de Google (útil para logs/depuración)

    Requisitos en settings.py:
      RECAPTCHA_SECRET_KEY (str)
      RECAPTCHA_MIN_SCORE (float, por defecto 0.5 opcional)
    """
    data = {
        "secret": getattr(settings, "RECAPTCHA_SECRET_KEY", ""),
        "response": token or "",
    }
    if remoteip:
        data["remoteip"] = remoteip

    # Validaciones básicas locales
    if not data["secret"]:
        return False, {"error": "missing-secret"}
    if not data["response"]:
        return False, {"error": "missing-token"}

    try:
        r = requests.post(VERIFY_URL, data=data, timeout=5)
        payload = r.json()
    except Exception as e:
        return False, {"error": f"request-failed: {e}"}

    # Criterios de validación v3
    min_score = float(getattr(settings, "RECAPTCHA_MIN_SCORE", 0.5))
    is_ok = (
        payload.get("success") is True
        and payload.get("action") == expected_action
        and float(payload.get("score", 0)) >= min_score
    )

    return is_ok, payload

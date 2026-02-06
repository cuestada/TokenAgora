import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# Importa el módulo completo (evita errores por nombres distintos según versión)
import agora_token.RtcTokenBuilder2 as rtc_mod

APP_ID = os.getenv("AGORA_APP_ID", "")
APP_CERT = os.getenv("AGORA_APP_CERTIFICATE", "")

app = FastAPI(title="Agora RTC Token Server (007)")

class TokenResponse(BaseModel):
    token: str


def _resolve_role(role: str):
    """
    Acepta role en varios formatos:
    - publisher / subscriber
    - RolePublisher / RoleSubscriber
    - host / audience / broadcaster, etc.
    Devuelve el objeto/constante que espera tu RtcTokenBuilder2.py,
    o un fallback numérico (1/2) si no existe.
    """
    r = (role or "").strip().lower()

    if r in ("rolepublisher", "publisher", "pub", "broadcaster", "host"):
        want = "publisher"
    elif r in ("rolesubscriber", "subscriber", "sub", "audience"):
        want = "subscriber"
    else:
        want = "publisher"

    pub = (
        getattr(rtc_mod, "Role_Publisher", None)
        or getattr(rtc_mod, "RolePublisher", None)
        or getattr(rtc_mod, "ROLE_PUBLISHER", None)
    )
    sub = (
        getattr(rtc_mod, "Role_Subscriber", None)
        or getattr(rtc_mod, "RoleSubscriber", None)
        or getattr(rtc_mod, "ROLE_SUBSCRIBER", None)
    )

    if want == "publisher":
        return pub if pub is not None else 1
    return sub if sub is not None else 2


def _build_token(app_id: str, app_cert: str, channel: str, uid: int, role_obj, ttl: int) -> str:
    """
    Llama a la firma correcta del builder según la versión que tengas copiada.
    Intenta varias opciones comunes.
    """
    # 1) Función suelta buildTokenWithUid(appId, appCert, channel, uid, role, tokenExpire, privilegeExpire)
    fn = getattr(rtc_mod, "buildTokenWithUid", None)
    if callable(fn):
        return fn(app_id, app_cert, channel, uid, role_obj, ttl, ttl)

    # 2) Variante snake_case
    fn = getattr(rtc_mod, "build_token_with_uid", None)
    if callable(fn):
        return fn(app_id, app_cert, channel, uid, role_obj, ttl)

    # 3) Clase RtcTokenBuilder2 / RtcTokenBuilder con método buildTokenWithUid
    cls = getattr(rtc_mod, "RtcTokenBuilder2", None) or getattr(rtc_mod, "RtcTokenBuilder", None)
    if cls is not None:
        m = getattr(cls, "buildTokenWithUid", None)
        if callable(m):
            return m(app_id, app_cert, channel, uid, role_obj, ttl, ttl)
        m = getattr(cls, "build_token_with_uid", None)
        if callable(m):
            return m(app_id, app_cert, channel, uid, role_obj, ttl)

    raise RuntimeError("No encuentro un método compatible en agora_token/RtcTokenBuilder2.py")


@app.get("/")
def root():
    # Evita 404 en el health-check de Render
    return {"status": "ok"}


@app.get("/health")
def health():
    # No expone secretos, solo indica si están configurados
    return {
        "ok": True,
        "has_app_id": bool(APP_ID),
        "has_app_cert": bool(APP_CERT),
    }


@app.get("/rtc/token", response_model=TokenResponse)
def rtc_token(
    channel: str = Query(..., min_length=1),
    uid: int = Query(..., ge=0),
    role: str = Query("publisher"),  # sin patrón estricto, aceptamos alias
    ttl: int = Query(3600, ge=60, le=86400),
):
    if not APP_ID or not APP_CERT:
        raise HTTPException(status_code=500, detail="Missing AGORA_APP_ID / AGORA_APP_CERTIFICATE")

    try:
        agora_role = _resolve_role(role)
        token = _build_token(APP_ID, APP_CERT, channel, uid, agora_role, ttl)
        return TokenResponse(token=token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token generation failed: {type(e).__name__}: {e}")

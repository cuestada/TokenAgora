import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# ajusta el import según dónde pegues los .py
import agora_token.RtcTokenBuilder2 as rtc_mod  # <-- import del módulo entero

APP_ID = os.getenv("AGORA_APP_ID", "")
APP_CERT = os.getenv("AGORA_APP_CERTIFICATE", "")

app = FastAPI(title="Agora RTC Token Server (007)")

class TokenResponse(BaseModel):
    token: str
def _resolve_role(role: str):
    r = (role or "").strip().lower()

    if r in ("rolepublisher", "publisher", "pub", "broadcaster", "host"):
        want = "publisher"
    elif r in ("rolesubscriber", "subscriber", "sub", "audience"):
        want = "subscriber"
    else:
        want = "publisher"

    pub = getattr(rtc_mod, "Role_Publisher", None) or getattr(rtc_mod, "RolePublisher", None) or getattr(rtc_mod, "ROLE_PUBLISHER", None)
    sub = getattr(rtc_mod, "Role_Subscriber", None) or getattr(rtc_mod, "RoleSubscriber", None) or getattr(rtc_mod, "ROLE_SUBSCRIBER", None)

    return (pub if pub is not None else 1) if want == "publisher" else (sub if sub is not None else 2)


# Endpoint health (opcional pero útil)
@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/rtc/token", response_model=TokenResponse)
def rtc_token(
    channel: str = Query(..., min_length=1),
    uid: int = Query(..., ge=0),
    role: str = Query("publisher"),
    ttl: int = Query(3600, ge=60, le=86400),
):
    if not APP_ID or not APP_CERT:
        raise HTTPException(500, "Missing AGORA_APP_ID / AGORA_APP_CERTIFICATE")

    agora_role = Role_Publisher if role == "publisher" else Role_Subscriber

    try:
        token = RtcTokenBuilder2.build_token_with_uid(
            APP_ID,
            APP_CERT,
            channel,
            uid,
            agora_role,
            ttl
        )
    except Exception as e:
        raise HTTPException(500, f"Token generation failed: {e}")

    return TokenResponse(token=token)


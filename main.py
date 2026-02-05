import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# ajusta el import según dónde pegues los .py
from agora_token.RtcTokenBuilder2 import RtcTokenBuilder2, Role_Publisher, Role_Subscriber

APP_ID = os.getenv("AGORA_APP_ID", "")
APP_CERT = os.getenv("AGORA_APP_CERTIFICATE", "")

app = FastAPI(title="Agora RTC Token Server (007)")

class TokenResponse(BaseModel):
    token: str

@app.get("/rtc/token", response_model=TokenResponse)
def rtc_token(
    channel: str = Query(..., min_length=1),
    uid: int = Query(..., ge=0),
    role: str = Query("publisher", pattern="^(publisher|subscriber)$"),
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


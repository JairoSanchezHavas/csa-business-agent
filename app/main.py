import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException, Query, Form, status
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings, logger, Settings
from app.database import init_db, get_db, MessageRecord
from app.security import verify_meta_signature
from app.whatsapp_client import WhatsAppClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando aplicacion y creando base de datos SQLite...")
    init_db()
    yield
    logger.info("Apagando aplicacion...")

app = FastAPI(
    title="WhatsApp Business API Webhook",
    description="Servidor modular y educativo para recepcion y envio de mensajes de WhatsApp.",
    version="1.0.0",
    lifespan=lifespan
)

templates = Jinja2Templates(directory="templates")

@app.get("/webhook", response_class=PlainTextResponse)
async def meta_handshake(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    settings: Settings = Depends(get_settings)
):
    logger.info(f"Handshake recibido. Mode: {hub_mode}")
    if hub_mode == "subscribe" and hub_verify_token == settings.VERIFY_TOKEN:
        logger.info("Handshake exitoso. Token verificado.")
        return PlainTextResponse(content=hub_challenge, status_code=200)

    logger.warning("Handshake fallido: Token incorrecto.")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token de verificacion invalido.")

@app.post("/webhook")
async def receive_webhook_event(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    raw_body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256")
    verify_meta_signature(raw_body, signature_header, settings.APP_SECRET)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        logger.error(f"Error parseando JSON: {e}")
        return {"status": "error_decoding_json"}

    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                val = change.get("value", {})
                contacts = val.get("contacts", [])
                sender_name = contacts[0]["profile"].get("name") if contacts and "profile" in contacts[0] else None

                for msg in val.get("messages", []):
                    msg_id = msg.get("id")
                    from_number = msg.get("from")
                    msg_type = msg.get("type", "unknown")
                    timestamp = msg.get("timestamp")

                    content = ""
                    if msg_type == "text":
                        content = msg.get("text", {}).get("body", "")
                    elif msg_type in ["image", "video", "audio", "document"]:
                        caption = msg.get(msg_type, {}).get("caption", "")
                        media_id = msg.get(msg_type, {}).get("id", "")
                        content = f"[{msg_type.upper()}] ID: {media_id} | {caption}".strip()
                    else:
                        content = f"[{msg_type.upper()}] {json.dumps(msg)}"

                    logger.info(f"Mensaje de {from_number} ({sender_name}): {content}")

                    existing = db.query(MessageRecord).filter(MessageRecord.message_id == msg_id).first()
                    if not existing:
                        record = MessageRecord(
                            message_id=msg_id,
                            sender=from_number,
                            sender_name=sender_name,
                            message_type=msg_type,
                            content=content,
                            timestamp=timestamp,
                            direction="INCOMING",
                            raw_payload=json.dumps(payload, ensure_ascii=False)
                        )
                        db.add(record)
                        db.commit()
    except Exception as err:
        logger.exception(f"Error al guardar evento: {err}")

    return {"status": "EVENT_RECEIVED"}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_view(
    request: Request,
    db: Session = Depends(get_db),
    status_msg: str = Query(None),
    status_type: str = Query("success")
):
    try:
        messages = db.query(MessageRecord).order_by(MessageRecord.created_at.desc()).limit(50).all()
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"messages": messages, "status_msg": status_msg, "status_type": status_type}
        )
    except Exception as exc:
        logger.exception(f"Error cargando dashboard: {exc}")
        raise HTTPException(status_code=500, detail=f"Error al cargar el dashboard: {str(exc)}")


@app.post("/dashboard/send")
async def send_manual_message(
    to_phone: str = Form(...),
    message_text: str = Form(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    client = WhatsAppClient(phone_number_id=settings.PHONE_NUMBER_ID, access_token=settings.WHATSAPP_TOKEN)
    try:
        resp = await client.send_text_message(to_phone=to_phone, text_body=message_text)
        outbound_id = resp.get("messages", [{}])[0].get("id")
        record = MessageRecord(
            message_id=outbound_id,
            sender=to_phone,
            sender_name="Dashboard Operador",
            message_type="text",
            content=message_text,
            direction="OUTBOUND",
            raw_payload=json.dumps(resp)
        )
        db.add(record)
        db.commit()
        return RedirectResponse(
            url=f"/dashboard?status_msg=Mensaje+enviado+a+{to_phone}&status_type=success",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as exc:
        logger.exception(f"Error enviando mensaje: {exc}")
        return RedirectResponse(
            url=f"/dashboard?status_msg=Error+enviando+mensaje:+{str(exc)}&status_type=error",
            status_code=status.HTTP_303_SEE_OTHER
        )

@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")

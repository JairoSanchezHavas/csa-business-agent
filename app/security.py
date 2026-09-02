import hmac
import hashlib
from fastapi import HTTPException, status
from app.config import logger

def verify_meta_signature(payload_bytes: bytes, signature_header: str | None, app_secret: str) -> bool:
    if not signature_header:
        logger.warning("Firma ausente: Falta el header X-Hub-Signature-256.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Falta el encabezado de firma X-Hub-Signature-256."
        )

    if not signature_header.startswith("sha256="):
        logger.warning("Firma malformada: No inicia con sha256=.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Formato de firma invalido. Se esperaba sha256=<hash>."
        )

    expected_hash = signature_header.split("sha256=", 1)[1].strip()
    secret_bytes = app_secret.encode("utf-8")
    mac = hmac.new(key=secret_bytes, msg=payload_bytes, digestmod=hashlib.sha256)
    calculated_hash = mac.hexdigest()

    if not hmac.compare_digest(expected_hash, calculated_hash):
        logger.error("Firma invalida: Hash calculado no coincide con Meta.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Firma HMAC-SHA256 invalida. Solicitud no autorizada."
        )

    return True

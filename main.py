import base64
import io

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel
from pyzbar import pyzbar

app = FastAPI(title="QR Code PIX Reader", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class BoletoRequest(BaseModel):
    image: str  # base64, com ou sem prefixo data:image/...


@app.post("/decode")
async def decode_boleto(body: BoletoRequest):
    b64 = body.image
    if "," in b64:
        b64 = b64.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(b64)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Imagem inválida: {exc}") from exc

    codes = pyzbar.decode(img)
    qr_codes = [c for c in codes if c.type == "QRCODE"]

    if not qr_codes:
        raise HTTPException(status_code=404, detail="Nenhum QR Code encontrado na imagem")

    return {"pix": qr_codes[0].data.decode("utf-8")}


@app.get("/health")
async def health():
    return {"status": "ok"}

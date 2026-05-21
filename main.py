import base64

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("formato de imagem não suportado")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Imagem inválida: {exc}") from exc

    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)

    if not data:
        raise HTTPException(status_code=404, detail="Nenhum QR Code encontrado na imagem")

    return {"pix": data}


@app.get("/health")
async def health():
    return {"status": "ok"}

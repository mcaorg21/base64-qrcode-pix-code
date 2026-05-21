import base64

import cv2
import fitz  # pymupdf
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
    image: str  # base64 de imagem (PNG/JPG) ou PDF, com ou sem prefixo data:...


def _decode_qr(img_bgr: np.ndarray) -> str | None:
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img_bgr)
    return data or None


def _pdf_to_frames(pdf_bytes: bytes) -> list[np.ndarray]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    frames = []
    for page in doc:
        # zoom 2x para melhorar a deteccao em PDFs de baixa resolucao
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_array = np.frombuffer(pix.samples, dtype=np.uint8)
        img = img_array.reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:  # RGBA -> BGR
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        else:  # RGB -> BGR
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        frames.append(img)
    return frames


@app.post("/decode")
async def decode_boleto(body: BoletoRequest):
    b64 = body.image
    if "," in b64:
        b64 = b64.split(",", 1)[1]

    try:
        raw = base64.b64decode(b64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Base64 inválido: {exc}") from exc

    is_pdf = raw[:4] == b"%PDF"

    if is_pdf:
        try:
            frames = _pdf_to_frames(raw)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"PDF inválido: {exc}") from exc
    else:
        img_array = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Formato de imagem não suportado")
        frames = [img]

    for frame in frames:
        pix_code = _decode_qr(frame)
        if pix_code:
            return {"pix": pix_code}

    raise HTTPException(status_code=404, detail="Nenhum QR Code encontrado")


@app.get("/health")
async def health():
    return {"status": "ok"}

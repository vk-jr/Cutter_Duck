from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import requests
from PIL import Image
from io import BytesIO
import os
import uuid

app = FastAPI()

HEADERS = {'User-Agent': 'Mozilla/5.0'}


def cut_with_mask(orig_bytes, mask_bytes, red_thresh=150, green_thresh=100, blue_thresh=100):
    original = Image.open(BytesIO(orig_bytes)).convert("RGBA")
    mask = Image.open(BytesIO(mask_bytes)).convert("RGB")
    if mask.size != original.size:
        mask = mask.resize(original.size)
    width, height = mask.size
    mask_data = mask.load()
    alpha = Image.new("L", (width, height), 0)
    alpha_data = alpha.load()
    for y in range(height):
        for x in range(width):
            r, g, b = mask_data[x, y]
            if r > red_thresh and g < green_thresh and b < blue_thresh:
                alpha_data[x, y] = 255
            else:
                alpha_data[x, y] = 0
    original.putalpha(alpha)
    bbox = original.getbbox()
    if bbox:
        original = original.crop(bbox)
    out = BytesIO()
    original.save(out, format="PNG")
    out.seek(0)
    return out


@app.post("/cut")
def cut_endpoint(payload: dict):
    orig_url = payload.get("original_url")
    mask_url = payload.get("mask_url")
    if not orig_url or not mask_url:
        raise HTTPException(status_code=400, detail="original_url and mask_url required")
    try:
        ro = requests.get(orig_url, headers=HEADERS, timeout=20)
        ro.raise_for_status()
        rm = requests.get(mask_url, headers=HEADERS, timeout=20)
        rm.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {e}")
    out = cut_with_mask(ro.content, rm.content)
    # If caller wants JSON with base64 or a URL, they can be added later.
    return StreamingResponse(out, media_type="image/png")

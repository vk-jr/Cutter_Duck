from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import requests
from PIL import Image, ImageFilter
from io import BytesIO
import os
import uuid

app = FastAPI()

HEADERS = {'User-Agent': 'Mozilla/5.0'}


import numpy as np

def cut_with_mask(orig_bytes, mask_bytes, diff_thresh=30):
    # Load images
    original = Image.open(BytesIO(orig_bytes)).convert("RGB")
    mask_img = Image.open(BytesIO(mask_bytes)).convert("RGB")
    
    # Ensure dimensions match
    if mask_img.size != original.size:
        mask_img = mask_img.resize(original.size)
            
    # Convert to numpy arrays
    arr_orig = np.array(original)
    arr_mask = np.array(mask_img)
    
    # conversion to int16 to avoid overflow during subtraction
    arr_orig = arr_orig.astype(np.int16)
    arr_mask = arr_mask.astype(np.int16)
    
    # Calculate absolute difference
    diff = np.abs(arr_orig - arr_mask)
    
    # Create mask: Pixel is 'Changed' AND 'Blue Dominant in Mask'
    # 1. Changed: Sum of absolute differences > threshold
    is_changed = np.sum(diff, axis=2) > diff_thresh
    
    # 2. Blue Dominant in Mask (Mask Blue > Red AND Mask Blue > Green)
    # Note: We need to use the original uint8 values for color comparison ideally, 
    # but the int16 is fine as values are same 0-255 range.
    m_r = arr_mask[:,:,0]
    m_g = arr_mask[:,:,1]
    m_b = arr_mask[:,:,2]
    is_blue = (m_b > m_r) & (m_b > m_g)
    
    # Combine: Changed AND Blue
    final_mask = is_changed & is_blue
    
    # Convert boolean mask to uint8 alpha channel (0 or 255)
    alpha_arr = (final_mask * 255).astype(np.uint8)
    
    # Create PIL image from alpha array
    alpha_img = Image.fromarray(alpha_arr, mode='L')
    
    # Clean up artifacts (rectangles)
    # Agressive Erosion to remove thicker lines (kernel size 17)
    alpha_img = alpha_img.filter(ImageFilter.MinFilter(17))
    # Dilation to restore shape
    alpha_img = alpha_img.filter(ImageFilter.MaxFilter(17))
    
    # Apply alpha to original
    original.putalpha(alpha_img)
    
    # Crop to content
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

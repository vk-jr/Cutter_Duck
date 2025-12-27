import sys
import os
import requests
from PIL import Image
from io import BytesIO

# ---------------------------------------------------------
# USAGE: python3 url_cutter.py <original_url> <mask_url> <output_path>
# ---------------------------------------------------------

if len(sys.argv) < 4:
    print("Error: Missing arguments. Usage: python3 url_cutter.py <orig_url> <mask_url> <output_path>")
    sys.exit(1)

# 1. Get URLs from n8n (instead of file paths)
original_url = sys.argv[1]
mask_url = sys.argv[2]
output_path = sys.argv[3]

print(f"Downloading Original: {original_url}")
print(f"Downloading Mask: {mask_url}")

try:
    # 2. Download Images directly into Memory
    # (We use a fake User-Agent so websites don't block the script)
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    resp_orig = requests.get(original_url, headers=headers, stream=True)
    resp_orig.raise_for_status() # Check for download errors
    
    resp_mask = requests.get(mask_url, headers=headers, stream=True)
    resp_mask.raise_for_status()

    # 3. Open Images with Pillow
    original = Image.open(BytesIO(resp_orig.content)).convert("RGBA")
    mask = Image.open(BytesIO(resp_mask.content)).convert("RGB")

    # 4. Resize Mask (Safety Step)
    if mask.size != original.size:
        mask = mask.resize(original.size)

    # 5. Process the Red Mask
    # (Same logic as before: Red = Keep, Background = Cut)
    width, height = mask.size
    mask_data = mask.load()

    # Create blank transparency layer
    alpha = Image.new("L", (width, height), 0)
    alpha_data = alpha.load()

    for y in range(height):
        for x in range(width):
            r, g, b = mask_data[x, y]
            # If pixel is RED, make it visible (255)
            if r > 150 and g < 100 and b < 100:
                alpha_data[x, y] = 255
            else:
                alpha_data[x, y] = 0

    # 6. Apply Cut & Crop
    original.putalpha(alpha)
    
    bbox = original.getbbox()
    if bbox:
        original = original.crop(bbox)

    # 7. Save to the Output Path
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    original.save(output_path, format="PNG")
    print(f"Success! Saved to: {output_path}")

except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
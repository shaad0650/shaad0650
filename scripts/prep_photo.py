"""Prep a photo for ASCII conversion: remove bg, boost contrast, composite on white.
Usage: python scripts/prep_photo.py source-photo.jpg
Outputs: source-prepped.png (grayscale) and source-mask.png (subject mask)."""
import sys
import cv2
import numpy as np
from PIL import Image
from rembg import remove

src = sys.argv[1] if len(sys.argv) > 1 else "source-photo.jpg"
rgba = remove(Image.open(src).convert("RGB")).convert("RGBA")   # 1. isolate subject
arr = np.array(rgba)
alpha = arr[:, :, 3].astype(np.float32) / 255.0

gray = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2GRAY)
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))      # 2. local contrast
gray = clahe.apply(gray).astype(np.float32)

out = gray * alpha + 255.0 * (1 - alpha)                          # 3. composite on white
Image.fromarray(out.astype(np.uint8), "L").save("source-prepped.png")
Image.fromarray((alpha * 255).astype(np.uint8), "L").save("source-mask.png")
print("wrote source-prepped.png + source-mask.png")

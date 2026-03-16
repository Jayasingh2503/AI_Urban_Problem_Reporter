from PIL import Image, ImageDraw
import os

def make_icon(size, path):
    img = Image.new('RGB', (size, size), color='#0d6efd')
    d = ImageDraw.Draw(img)
    d.ellipse([size//4, size//4, 3*size//4, 3*size//4], fill='white')
    img.save(path)

os.makedirs('static', exist_ok=True)
make_icon(192, 'static/icon-192.png')
make_icon(512, 'static/icon-512.png')
print('Icons created!')
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Apheenx.settings')
django.setup()

from product.models import Product, ProductImage

try:
    p = Product.objects.get(id=84)
    print(f"Product Name: {p.name}")
    images = p.images.all()
    if images.exists():
        print("Images found in Database:")
        for img in images:
            print(f" - {img.image.name}")
    else:
        print("No images found in the database for this product! (Record was deleted)")
except Exception as e:
    print(f"Error: {e}")

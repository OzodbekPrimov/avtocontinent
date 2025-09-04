#!/usr/bin/env python
"""
Test script to verify that ProductForm properly displays existing price values
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from store.models import Product
from dashboard.forms import ProductForm

def test_product_form_price_display():
    """Test that ProductForm displays existing price values when editing"""
    print("Testing ProductForm price field initialization...")
    
    # Get a product from database
    try:
        product = Product.objects.first()
        if not product:
            print("No products found in database. Please create a product first.")
            return
        
        print(f"Testing with product: {product.name_uz or 'Unnamed'}")
        print(f"Product price_usd: {product.price_usd}")
        
        # Create form with product instance
        form = ProductForm(instance=product)
        
        # Check if price_usd field has the correct initial value
        price_field = form.fields['price_usd']
        print(f"Form field initial value: {price_field.initial}")
        print(f"Form field value: {form['price_usd'].value()}")
        
        # Test that the initial value matches the product's price
        if price_field.initial == product.price_usd:
            print("✅ SUCCESS: Price field initial value is correctly set!")
        else:
            print("❌ FAILED: Price field initial value doesn't match product price")
            print(f"Expected: {product.price_usd}, Got: {price_field.initial}")
        
        # Test other fields as well
        print("\nTesting other fields:")
        print(f"Stock quantity - Product: {product.stock_quantity}, Form: {form.fields['stock_quantity'].initial}")
        print(f"SKU - Product: {product.sku}, Form: {form.fields['sku'].initial}")
        print(f"Is active - Product: {product.is_active}, Form: {form.fields['is_active'].initial}")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_product_form_price_display()

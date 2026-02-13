from decimal import Decimal
from django.conf import settings
from store.models import Product

class Cart(object):
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart
        self.seller_id = self.session.get('cart_seller_id', None)

    def add(self, product, quantity_kg=1):
        product_id = str(product.id)
        seller_id = str(product.seller.id)

        # Enforce One-Seller Rule
        if self.seller_id and self.seller_id != seller_id:
            raise ValueError("You can only order from one seller at a time.")

        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price': str(product.price_per_kg)}
        
        # Update quantity (assuming overwrite or add logic based wholly on user input for now)
        # Using float for JSON serialization
        current_qty = self.cart[product_id].get('quantity', 0)
        self.cart[product_id]['quantity'] = float(quantity_kg) 
        # Alternatively: = current_qty + float(quantity_kg) if we want additive behavior
        
        # Set seller
        if not self.seller_id:
            self.seller_id = seller_id
            self.session['cart_seller_id'] = seller_id
        
        self.save()

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()
        
        if not self.cart:
            self.clear()

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        
        # IMPORTANT: Deep copy to avoid polluting the session with non-serializable Product objects
        cart = self.cart.copy()
        for key in cart:
            cart[key] = cart[key].copy()

        for product in products:
            cart[str(product.id)]['product'] = product

        for item in cart.values():
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * Decimal(item['quantity'])
            yield item
    
    def __len__(self):
        return len(self.cart.keys())

    def get_total_price(self):
        return sum(Decimal(item['price']) * Decimal(item['quantity']) for item in self.cart.values())

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        if 'cart_seller_id' in self.session:
            del self.session['cart_seller_id']
        self.session.modified = True

    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True

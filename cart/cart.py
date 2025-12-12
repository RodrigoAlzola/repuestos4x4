from store.models import Product, Profile

class Cart():
    def __init__(self, request):
        self.session = request.session
        self.request = request

        # Get the actual session
        cart = self.session.get('session_key')

        if 'session_key' not in request.session:
            cart = self.session['session_key'] = {}

        self.cart = cart

    def add(self, product, quantity):
        product_id = str(product.id)
        product_quantity = int(quantity)
        
        # Determinar si es internacional
        is_international = product.stock <= 0 and product.stock_international > 0
        
        if product_id in self.cart:
            # Si ya existe, actualizar cantidad e info internacional
            if isinstance(self.cart[product_id], dict):
                self.cart[product_id]['quantity'] = product_quantity
                self.cart[product_id]['is_international'] = is_international
            else:
                # Migrar formato viejo a nuevo
                self.cart[product_id] = {
                    'quantity': product_quantity,
                    'is_international': is_international
                }
        else:
            # Nuevo formato con diccionario
            self.cart[product_id] = {
                'quantity': product_quantity,
                'is_international': is_international
            }

        self.session.modified = True

        # Log in user
        if self.request.user.is_authenticated:
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            carty = str(self.cart)
            carty = carty.replace("'", '"')
            current_user.update(old_cart=carty)

    def db_add(self, product_id, quantity):
        product_id = str(product_id)
        product_quantity = int(quantity)
        
        # Buscar el producto para determinar si es internacional
        try:
            product = Product.objects.get(id=product_id)
            is_international = product.stock <= 0 and product.stock_international > 0
        except Product.DoesNotExist:
            is_international = False
        
        if product_id in self.cart:
            if isinstance(self.cart[product_id], dict):
                self.cart[product_id]['quantity'] = product_quantity
                self.cart[product_id]['is_international'] = is_international
            else:
                self.cart[product_id] = {
                    'quantity': product_quantity,
                    'is_international': is_international
                }
        else:
            self.cart[product_id] = {
                'quantity': product_quantity,
                'is_international': is_international
            }

        self.session.modified = True

        # Log in user
        if self.request.user.is_authenticated:
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            carty = str(self.cart)
            carty = carty.replace("'", '"')
            current_user.update(old_cart=str(carty))

    def __len__(self):
        return len(self.cart)
    
    def get_products(self):
        # Get ids from cart
        product_ids = self.cart.keys()

        # Use ids to look in DB
        products = Product.objects.filter(id__in=product_ids)

        return products

    def get_quants(self):
        """Retorna cantidades en formato compatible"""
        quantities = {}
        for product_id, value in self.cart.items():
            if isinstance(value, dict):
                quantities[product_id] = value['quantity']
            else:
                # Formato viejo (solo número)
                quantities[product_id] = value
        return quantities
    
    def get_international_status(self):
        """Retorna qué productos son internacionales"""
        international_status = {}
        for product_id, value in self.cart.items():
            if isinstance(value, dict):
                international_status[product_id] = value.get('is_international', False)
            else:
                # Formato viejo, verificar en base de datos
                try:
                    product = Product.objects.get(id=product_id)
                    international_status[product_id] = product.stock <= 0 and product.stock_international > 0
                except Product.DoesNotExist:
                    international_status[product_id] = False
        return international_status
    
    def has_international_items(self):
        """Verifica si el carrito tiene productos internacionales"""
        return any(self.get_international_status().values())
    
    def update(self, product, quantity):
        product_id = str(product)
        product_quantity = int(quantity)

        if product_id in self.cart:
            if isinstance(self.cart[product_id], dict):
                self.cart[product_id]['quantity'] = product_quantity
            else:
                # Mantener compatibilidad con formato viejo
                self.cart[product_id] = product_quantity

        self.session.modified = True

        # Log in user
        if self.request.user.is_authenticated:
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            carty = str(self.cart)
            carty = carty.replace("'", '"')
            current_user.update(old_cart=carty)

    def delete(self, product):
        product_id = str(product)

        if product_id in self.cart:
            del self.cart[product_id]

        self.session.modified = True

        # Log in user
        if self.request.user.is_authenticated:
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            carty = str(self.cart)
            carty = carty.replace("'", '"')
            current_user.update(old_cart=carty)

    def cart_total(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        quantities = self.get_quants()  # Usar get_quants() para compatibilidad
        total = 0
        
        for key, value in quantities.items():
            key = int(key)
            for product in products:
                if product.id == key:
                    if product.is_sale:
                        total = total + (product.sale_price * int(value))
                    else:
                        total = total + (product.price * int(value))
        return total
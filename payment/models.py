from django.db import models
from django.contrib.auth.models import User
from store.models import Product
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from payment.validators import validar_rut
import datetime

class ShippingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shipping_addresses')
    full_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=20)
    id_number = models.CharField(max_length=10, default='', validators=[validar_rut], help_text='Formato: 12345678-9')
    address1 = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    commune = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100)
    zipcode = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default='Chile')
    
    # NUEVO: Campo de comentarios
    notes = models.TextField(
        blank=True, 
        null=True,
        max_length=300,
        verbose_name='Comentarios adicionales',
        help_text='Ej: "Dejar con conserje", "Timbre no funciona", "Casa blanca con reja negra"'
    )
    
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name_plural = "Shipping Addresses"
    
    def __str__(self):
        return f"{self.full_name} - {self.address1}, {self.city}"
    
    def save(self, *args, **kwargs):
        if not self.pk and not ShippingAddress.objects.filter(user=self.user).exists():
            self.is_default = True
        
        if self.is_default:
            ShippingAddress.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)
    
# Create a Shipping Address by default when user sign up
#def create_shipping(sender, instance, created, **kwargs):
#    if created:
#        user_shipping= ShippingAddress(user=instance)
#        user_shipping.save()

# Automate the profile
# post_save.connect(create_shipping, sender=User)



class Order(models.Model):
    # Información del comprador (SIEMPRE del usuario)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=250)
    email = models.EmailField(max_length=250)
    phone = models.CharField(max_length=20)
    id_number = models.CharField(max_length=10, default='', validators=[validar_rut], help_text='Formato: 12345678-9')
    
    # Información de envío (puede ser domicilio o taller)
    shipping_address = models.TextField(max_length=15000)
    workshop = models.ForeignKey('workshop.Workshop', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Información de la orden
    amount_pay = models.DecimalField(max_digits=10, decimal_places=2)
    date_order = models.DateTimeField(auto_now_add=True)
    shipped = models.BooleanField(default=False)
    date_shipped = models.DateTimeField(blank=True, null=True)
    has_international_items = models.BooleanField(default=False)

    # Buy order - generado automáticamente
    buy_order = models.CharField(max_length=50, unique=True, null=True, blank=True, db_index=True)

    # Informacion de pago
    transaction_date = models.DateTimeField(null=True, blank=True)
    authorization_code = models.CharField(max_length=50, null=True, blank=True)
    payment_type_code = models.CharField(max_length=10, null=True, blank=True)  # VD, VN, etc.
    installments_number = models.IntegerField(null=True, blank=True)
    card_number = models.CharField(max_length=20, null=True, blank=True)  # últimos 4 dígitos
    session_id = models.CharField(max_length=100, null=True, blank=True)
    accounting_date = models.CharField(max_length=10, null=True, blank=True)
    transaction_status = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        ordering = ['-date_order']
    
    def save(self, *args, **kwargs):
        """Genera buy_order automáticamente si no existe"""
        if not self.buy_order:
            # Primera guardada sin buy_order
            is_new = self.pk is None
            super().save(*args, **kwargs)
            
            # Generar buy_order basado en ID y fecha
            if is_new:
                # Formato: 4X4-YYYYMMDD-XXXXXX
                # Ejemplo: 4X4-20241223-000001
                date_str = self.date_order.strftime('%Y%m%d')
                self.buy_order = f"4X4-{date_str}-{self.id:06d}"
                super().save(update_fields=['buy_order'])
        else:
            super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Order #{self.id} - {self.buy_order or 'Pending'} - {self.full_name}"
    
    def get_payment_type_display(self):
        """Retorna el tipo de pago en español"""
        payment_types = {
            'VD': 'Débito',
            'VN': 'Crédito',
            'VC': 'Crédito',
            'SI': 'Crédito sin interés',
            'S2': 'Crédito 2 cuotas sin interés',
            'NC': 'Crédito sin interés',
        }
        return payment_types.get(self.payment_type_code, 'No especificado')
    
# Auto add shipping date
@receiver(pre_save, sender=Order)
def set_shipped_date_on_update(sender, instance, **kwargs):
    if instance.pk:
        now = datetime.datetime.now()
        obj = sender._default_manager.get(pk=instance.pk)
        if instance.shipped and not obj.shipped:
            instance.date_shipped = now
    

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    quantity = models.PositiveBigIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_international = models.BooleanField(default=False)

    def get_total(self):
        return self.price * self.quantity

    def __str__(self):
        return f'Order Item - {str(self.id)}'
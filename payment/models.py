from django.db import models
from django.contrib.auth.models import User
from store.models import Product
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import datetime

class ShippingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shipping_addresses')
    full_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=20)
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
    
    # Información de envío (puede ser domicilio o taller)
    shipping_address = models.TextField(max_length=15000)
    workshop = models.ForeignKey('workshop.Workshop', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Información de la orden
    amount_pay = models.DecimalField(max_digits=10, decimal_places=2)
    date_order = models.DateTimeField(auto_now_add=True)
    shipped = models.BooleanField(default=False)
    date_shipped = models.DateTimeField(blank=True, null=True)
    has_international_items = models.BooleanField(default=False)

    def __str__(self):
        return f'Order - {str(self.id)}'
    
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
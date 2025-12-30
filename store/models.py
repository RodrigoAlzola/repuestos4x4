from django.db import models
import datetime
from django.contrib.auth.models import User
from django.db.models.signals import post_save


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, blank=False)
    date_modified = models.DateTimeField(User, auto_now=True)
    phone = models.CharField(max_length=20, blank=False)
    email = models.EmailField(max_length=100, blank=False)
    address1 = models.CharField(max_length=200, blank=True)
    address2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=True)
    state = models.CharField(max_length=200, blank=True)
    commune = models.CharField(max_length=200, blank=True)
    zipcode = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=200, blank=True)
    old_cart = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.user.username
    
# Create a User by default when user sign up
def create_profile(sender, instance, created, **kwargs):
    if created:
        user_profile = Profile(user=instance)
        user_profile.save()

# Automate the profile
post_save.connect(create_profile, sender=User)


class Category(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Customer(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=10)
    email = models.EmailField(max_length=100)
    password = models.CharField(max_length=100)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Provider(models.Model):
    name = models.CharField(max_length=50, blank=False)
    contact_name = models.CharField(max_length=50, blank=False)
    phone = models.CharField(max_length=20, blank=False)
    email = models.CharField(max_length=20, blank=True)
    address1 = models.CharField(max_length=200, blank=True)
    address2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=True)
    state = models.CharField(max_length=200, blank=True)
    commune = models.CharField(max_length=200, blank=True)
    zipcode = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(upload_to='providers/logos/', blank=True, null=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)
    name = models.CharField(max_length=100)
    part_number = models.CharField(max_length=50, default='', blank=True, null=True)
    price = models.DecimalField(default=0, decimal_places=2, max_digits=10)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, default=1)
    subcategory = models.CharField(max_length=100, default='', blank=True, null=True)
    description = models.CharField(max_length=250, default='', blank=True, null=True)
    image = models.URLField(max_length=500, blank=True, null=True) # models.ImageField(upload_to='uploads/product/')
    is_sale = models.BooleanField(default=False)
    sale_price = models.DecimalField(default=0, decimal_places=2, max_digits=10)
    weight_kg = models.DecimalField(default=0, decimal_places=3, max_digits=10)
    length_cm = models.DecimalField(default=0, decimal_places=3, max_digits=10)
    height_cm = models.DecimalField(default=0, decimal_places=3, max_digits=10)
    width_cm = models.DecimalField(default=0, decimal_places=3, max_digits=10)
    volume_m3 = models.DecimalField(default=0, decimal_places=6, max_digits=15)
    motor = models.CharField(max_length=100, default='', blank=True, null=True)
    stock = models.IntegerField(default=0)
    stock_international = models.IntegerField(default=0)
    tariff_code = models.CharField(max_length=50, default='', blank=True, null=True)
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, null=True, blank=True)
    recommended_quantities = models.CharField(max_length=200, default='', blank=True, null=True)

    def __str__(self):
        return f"{self.part_number} - {self.name}"

class Compatibility(models.Model):
    product = models.ForeignKey(Product, related_name='compatibilities', on_delete=models.CASCADE)
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    serie = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.brand} {self.model} {self.serie}"


# Guest Users
class GuestUser(models.Model):
    full_name = models.CharField(max_length=100, blank=False)
    date = models.DateTimeField(auto_now=True)
    phone = models.CharField(max_length=20, blank=False)
    email = models.EmailField(max_length=100, blank=False)
    address1 = models.CharField(max_length=200, blank=False)
    address2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=False)
    state = models.CharField(max_length=200, blank=True)
    commune = models.CharField(max_length=200, blank=False)
    zipcode = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=200, blank=False)

    def __str__(self):
        return self.full_name



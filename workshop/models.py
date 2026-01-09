from django.db import models
from PIL import Image


# Create your models here.

class Workshop(models.Model):
    name = models.CharField(max_length=50, blank=False)
    contact_name = models.CharField(max_length=50, blank=False)
    phone = models.CharField(max_length=20, blank=False)
    email = models.CharField(max_length=20, blank=True)
    id_number = models.CharField(max_length=10, default='')
    address1 = models.CharField(max_length=200, blank=True)
    address2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=True)
    state = models.CharField(max_length=200, blank=True)
    commune = models.CharField(max_length=200, blank=True)
    zipcode = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(upload_to='workshop/logos/', blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.logo:
            img_path = self.logo.path
            img = Image.open(img_path)

            max_size = (300, 300)  # Set your desired dimensions
            img.resize(max_size, Image.Resampling.LANCZOS)
            img.save(img_path)


    def __str__(self):
        return self.name
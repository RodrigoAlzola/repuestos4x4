from django import forms
from .models import ShippingAddress

from django import forms
from .models import ShippingAddress

from django import forms
from .models import ShippingAddress

from django import forms
from .models import ShippingAddress

from django import forms
from .models import ShippingAddress

class ShippingForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = ['full_name', 'email', 'phone', 'id_number', 'address1', 'address2', 
                  'city', 'commune', 'region', 'zipcode', 'country', 'notes']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombre completo'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 
                'placeholder': 'correo@ejemplo.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '+56 9 1234 5678'
            }),
            'id_number': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'RUT (ej: 12345678-9)'
            }),
            'address1': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Calle y número'
            }),
            'address2': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Depto, oficina (opcional)'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Santiago'
            }),
            'commune': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'La Florida'
            }),
            'region': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Región Metropolitana'
            }),
            'zipcode': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '7550000'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Chile'
            }),  # ← Campo visible ahora
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Ej: "Dejar con conserje", "Timbre no funciona", "Casa con reja negra"'
            }),
        }
        labels = {
            'notes': 'Comentarios adicionales (opcional)',
            'country': 'País',
        }

class PaymentForm(forms.Form):
    card_name = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Card Name'}), required=True)
    card_id_number = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RUT (ej: 12345678-9)'}), required=True)
    card_number = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Card Number'}), required=True)
    card_exp_date = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Expiration Date'}), required=True)
    card_cvv_number = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' CVV'}), required=True)
    card_address1 = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Billing Address 1'}), required=True)
    card_address2 = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Billing Address 2'}), required=False)
    card_city = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Billing City'}), required=True)
    card_state = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Billing State'}), required=True)
    card_zipcode = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Billing Zipcode'}), required=False)
    card_commune = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Billing Commune'}), required=False)
    card_country = forms.CharField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Billing Country'}), required=True)

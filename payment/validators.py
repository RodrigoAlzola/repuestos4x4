from django.core.exceptions import ValidationError
import re

def validar_rut(rut):
    """
    Valida un RUT chileno
    Acepta formatos: 12345678-9, 12.345.678-9, 123456789
    """
    if not rut:
        return
    
    # Limpiar el RUT (quitar puntos y guiones)
    rut_limpio = rut.replace(".", "").replace("-", "").upper()
    
    # Verificar que tenga entre 8 y 9 caracteres
    if len(rut_limpio) < 8 or len(rut_limpio) > 9:
        raise ValidationError('RUT inválido: debe tener entre 8 y 9 caracteres')
    
    # Separar número y dígito verificador
    rut_numero = rut_limpio[:-1]
    digito_verificador = rut_limpio[-1]
    
    # Verificar que el número sea numérico
    if not rut_numero.isdigit():
        raise ValidationError('RUT inválido: debe contener solo números')
    
    # Calcular dígito verificador
    suma = 0
    multiplo = 2
    
    for digito in reversed(rut_numero):
        suma += int(digito) * multiplo
        multiplo += 1
        if multiplo == 8:
            multiplo = 2
    
    resto = suma % 11
    dv_calculado = 11 - resto
    
    # Convertir a string
    if dv_calculado == 11:
        dv_calculado = '0'
    elif dv_calculado == 10:
        dv_calculado = 'K'
    else:
        dv_calculado = str(dv_calculado)
    
    # Comparar
    if digito_verificador != dv_calculado:
        raise ValidationError(f'RUT inválido: dígito verificador incorrecto')
    
    return True
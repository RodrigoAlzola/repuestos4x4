from django.shortcuts import redirect

class DomainRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().lower()
        
        # Redirigir repuesto4x4.com a 4x4max.cl
        if 'repuesto4x4.com' in host:
            # Construir nueva URL con el dominio correcto
            new_url = request.build_absolute_uri().replace(
                host, '4x4max.cl'
            )
            return redirect(new_url, permanent=True)
        
        # Redirigir www.4x4max.cl a 4x4max.cl (opcional)
        if host == 'www.4x4max.cl':
            new_url = request.build_absolute_uri().replace(
                'www.4x4max.cl', '4x4max.cl'
            )
            return redirect(new_url, permanent=True)
        
        return self.get_response(request)
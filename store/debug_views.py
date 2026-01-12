# debug_views.py
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import socket
import os

@csrf_exempt
def test_smtp_debug(request):
    """Endpoint temporal para debug SMTP"""
    
    # Seguridad básica
    secret = request.GET.get('key')
    if secret != 'debug2025':  # Cambia esto por algo más seguro
        return HttpResponse('Forbidden', status=403)
    
    lines = []
    lines.append("=" * 60)
    lines.append("RAILWAY SMTP DEBUG REPORT")
    lines.append("=" * 60)
    
    # Configuración
    lines.append("\n📧 EMAIL SETTINGS:")
    lines.append(f"  Backend: {settings.EMAIL_BACKEND}")
    lines.append(f"  Host: {settings.EMAIL_HOST}")
    lines.append(f"  Port: {settings.EMAIL_PORT}")
    lines.append(f"  Use TLS: {getattr(settings, 'EMAIL_USE_TLS', False)}")
    lines.append(f"  Use SSL: {getattr(settings, 'EMAIL_USE_SSL', False)}")
    lines.append(f"  User: {settings.EMAIL_HOST_USER}")
    lines.append(f"  Password: {'SET ✓' if settings.EMAIL_HOST_PASSWORD else 'NOT SET ✗'}")
    lines.append(f"  Timeout: {getattr(settings, 'EMAIL_TIMEOUT', 'default')}")
    lines.append(f"  From: {settings.DEFAULT_FROM_EMAIL}")
    
    # Environment
    lines.append("\n🌍 ENVIRONMENT:")
    lines.append(f"  Railway: {os.getenv('RAILWAY_ENVIRONMENT', 'NOT DETECTED')}")
    lines.append(f"  Settings: {os.getenv('DJANGO_SETTINGS_MODULE', 'NOT SET')}")
    
    # Test puertos
    lines.append("\n🔌 PORT CONNECTIVITY:")
    host = settings.EMAIL_HOST
    
    for port in [587, 465]:
        lines.append(f"\n  Port {port}:")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            result = sock.connect_ex((host, port))
            
            if result == 0:
                lines.append(f"    ✅ OPEN - Connection successful")
                sock.close()
                
                # Test handshake
                try:
                    import smtplib
                    if port == 465:
                        lines.append(f"    Testing SSL...")
                        s = smtplib.SMTP_SSL(host, port, timeout=15)
                        s.quit()
                        lines.append(f"    ✅ SSL handshake OK")
                    else:
                        lines.append(f"    Testing STARTTLS...")
                        s = smtplib.SMTP(host, port, timeout=15)
                        s.starttls()
                        s.quit()
                        lines.append(f"    ✅ STARTTLS OK")
                except Exception as e:
                    lines.append(f"    ⚠️  Handshake error: {str(e)[:100]}")
            else:
                lines.append(f"    ❌ BLOCKED (error code: {result})")
        except socket.timeout:
            lines.append(f"    ❌ TIMEOUT after 15 seconds")
        except Exception as e:
            lines.append(f"    ❌ Error: {str(e)[:100]}")
    
    # Test autenticación
    lines.append("\n🔐 AUTHENTICATION TEST:")
    try:
        import smtplib
        port = settings.EMAIL_PORT
        use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
        use_tls = getattr(settings, 'EMAIL_USE_TLS', False)
        
        lines.append(f"  Attempting with port {port}, SSL={use_ssl}, TLS={use_tls}")
        
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            if use_tls:
                server.starttls()
        
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        lines.append("  ✅ LOGIN SUCCESSFUL")
        server.quit()
        
    except socket.timeout:
        lines.append("  ❌ LOGIN TIMEOUT")
    except Exception as e:
        lines.append(f"  ❌ LOGIN FAILED: {str(e)[:200]}")
    
    # Test de envío
    if request.GET.get('send') == 'yes':
        lines.append("\n📨 EMAIL SEND TEST:")
        try:
            from django.core.mail import send_mail
            send_mail(
                'Test Railway',
                'Test email body',
                settings.DEFAULT_FROM_EMAIL,
                [settings.EMAIL_HOST_USER],
                fail_silently=False,
            )
            lines.append("  ✅ EMAIL SENT")
        except Exception as e:
            lines.append(f"  ❌ SEND FAILED: {str(e)[:200]}")
    
    lines.append("\n" + "=" * 60)
    lines.append("Add &send=yes to URL to test actual email sending")
    lines.append("=" * 60)
    
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
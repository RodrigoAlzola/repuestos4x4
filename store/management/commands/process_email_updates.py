import os
import zipfile
import tempfile
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from imap_tools import MailBox, AND
from decouple import config

class Command(BaseCommand):
    help = 'Procesa emails con archivos CSV de actualización de productos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mark-as-read',
            action='store_true',
            help='Marcar emails como leídos después de procesarlos',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('📧 Conectando al servidor de correo...'))
        
        try:
            # Configuración del servidor de correo
            email_host = config('EMAIL_HOST_SUPPORT', default='imap.zoho.com')
            email_port = config('EMAIL_PORT_SUPPORT', default=993, cast=int)
            email_user = config('EMAIL_USER_SUPPORT')
            email_password = config('EMAIL_PASSWORD_SUPPORT')
            subject_filter = config('EMAIL_SUBJECT_FILTER_SUPPORT', default='Price Detail')
            
            # Conectar al servidor IMAP
            with MailBox(email_host).login(email_user, email_password) as mailbox:
                criteria = AND(seen=False)
                all_unread = list(mailbox.fetch(criteria))

                self.stdout.write(f'🔍 Total emails no leídos: {len(all_unread)}')

                # Mostrar asuntos de todos los no leídos
                for msg in all_unread:
                    self.stdout.write(f'   📧 Asunto: "{msg.subject}"')

                # Filtrar manualmente
                messages = []
                for msg in all_unread:
                    if subject_filter.lower() in msg.subject.lower():
                        messages.append(msg)
                        self.stdout.write(f'   ✅ MATCH: "{msg.subject}"')

                if not messages:
                    self.stdout.write(self.style.WARNING(f'📭 No hay emails que coincidan con: "{subject_filter}"'))
                    return
                
                self.stdout.write(self.style.SUCCESS(f'📬 Se encontraron {len(messages)} email(s) nuevos'))
                
                for msg in messages:
                    self.stdout.write(f'\n📨 Procesando email: {msg.subject}')
                    self.stdout.write(f'   De: {msg.from_}')
                    self.stdout.write(f'   Fecha: {msg.date}')
                    
                    # Procesar archivos adjuntos
                    processed = False
                    for att in msg.attachments:
                        if att.filename.endswith('.zip'):
                            self.stdout.write(f'📦 Archivo encontrado: {att.filename}')
                            
                            # Crear directorio temporal
                            with tempfile.TemporaryDirectory() as temp_dir:
                                # Guardar archivo ZIP
                                zip_path = os.path.join(temp_dir, att.filename)
                                with open(zip_path, 'wb') as f:
                                    f.write(att.payload)
                                
                                # Descomprimir
                                self.stdout.write('📂 Descomprimiendo archivo...')
                                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                                    zip_ref.extractall(temp_dir)
                                
                                # Buscar archivo CSV
                                csv_file = None
                                for file in os.listdir(temp_dir):
                                    if file.endswith('.csv'):
                                        csv_file = os.path.join(temp_dir, file)
                                        break
                                
                                if csv_file:
                                    self.stdout.write(f'✅ CSV encontrado: {os.path.basename(csv_file)}')
                                    
                                    # Ejecutar comando de actualización
                                    self.stdout.write(self.style.WARNING('\n🔄 Iniciando actualización de productos...'))
                                    try:
                                        call_command('update_products', csv_file)
                                        self.stdout.write(self.style.SUCCESS('✅ Actualización completada exitosamente'))
                                        processed = True
                                    except Exception as e:
                                        self.stderr.write(self.style.ERROR(f'❌ Error al actualizar productos: {e}'))
                                else:
                                    self.stderr.write(self.style.ERROR('❌ No se encontró archivo CSV en el ZIP'))
                    
                    # Marcar como leído si se procesó correctamente
                    if processed and options['mark_as_read']:
                        mailbox.flag(msg.uid, ['\\Seen'], True)
                        self.stdout.write('✉️ Email marcado como leído')
                
                self.stdout.write(self.style.SUCCESS('\n✅ Proceso completado'))
                
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Error al procesar emails: {e}'))
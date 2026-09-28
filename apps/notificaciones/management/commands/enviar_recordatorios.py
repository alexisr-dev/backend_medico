from django.core.management.base import BaseCommand

from apps.notificaciones.services import procesar_recordatorios_pendientes


class Command(BaseCommand):
    help = "Envia los recordatorios de citas cuya fecha programada ya vencio."

    def handle(self, *args, **options):
        resultado = procesar_recordatorios_pendientes()
        self.stdout.write(
            self.style.SUCCESS(
                f"Recordatorios enviados: {resultado['enviados']} | fallidos: {resultado['fallidos']}"
            )
        )

from django.db import models

class Auditoria(models.Model):
    # Campos básicos de información
    fecha_creacion = models.DateTimeField(auto_now_add=True) # Se llena solo con la fecha actual
    
    # El archivo que sube el usuario
    archivo_soat = models.FileField(upload_to='soportes_soat/') 
    
    # Datos que la IA va a "leer" (al principio estarán vacíos)
    placa_detectada = models.CharField(max_length=10, blank=True, null=True)
    monto_detectado = models.CharField(max_length=50, blank=True, null=True)
    
    # El veredicto del sistema
    RESULTADOS = [
        ('PENDIENTE', 'Pendiente de Análisis'),
        ('APROBADO', 'Aprobado'),
        ('FRAUDE', 'Posible Fraude'),
    ]
    resultado = models.CharField(max_length=20, choices=RESULTADOS, default='PENDIENTE')

    def __str__(self):
        return f"Auditoria {self.id} - {self.fecha_creacion}"
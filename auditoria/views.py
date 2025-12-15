from django.shortcuts import render, redirect, get_object_or_404 # <--- Agrega get_object_or_404
from django.contrib import messages # <--- IMPORTANTE: Para mandar mensajes al HTML
from .forms import CargaForm
from .models import Auditoria  # <--- IMPORTANTE: Traemos la tabla
# Importamos tu nuevo script lector
from .OCR.lector_soat import extraer_datos_soat 
# Importamos la nueva función
from .OCR.cliente_api import consultar_runt_publico

def carga_soportes(request):
    if request.method == 'POST':
        form = CargaForm(request.POST, request.FILES)
        if form.is_valid():
            # 1. Guardamos temporalmente para tener el archivo en disco
            auditoria = form.save()
            
            # 2. Ejecutamos tu Super Script
            try:
                ruta_pdf = auditoria.archivo_soat.path
                resultado_ocr = extraer_datos_soat(ruta_pdf)
                
                # 3. VERIFICAMOS SI TUVO ÉXITO
                if resultado_ocr['exito']:
                    # --- ÉXITO: Guardamos datos y auditamos ---
                    auditoria.placa_detectada = resultado_ocr['placa']
                    auditoria.monto_detectado = resultado_ocr['monto']
                    
                    # Validación API (El Juez)
                    api_check = consultar_runt_publico(resultado_ocr['placa'])
                    
                    if api_check['existe']:
                         # Lógica inversa: Si está en la lista de activos, lo marcamos FRAUDE (según tu indicación)
                        auditoria.resultado = 'FRAUDE'
                        # auditoria.reporte_ia = ... (Aquí llamarías a tu generador GPT si quieres)
                    else:
                        auditoria.resultado = 'APROBADO'
                    
                    auditoria.save()
                    messages.success(request, f"¡Lectura exitosa! Placa: {resultado_ocr['placa']}")
                    return redirect('dashboard')
                
                else:
                    # --- FALLO: El OCR no leyó nada ---
                    # 1. Borramos el registro y el archivo basura
                    auditoria.archivo_soat.delete() # Borra archivo
                    auditoria.delete() # Borra de BD
                    
                    # 2. Mandamos el mensaje de error al usuario
                    messages.error(request, f"❌ {resultado_ocr['mensaje']}")
                    # Nos quedamos en la misma página para que intente de nuevo
            
            except Exception as e:
                # Error catastrófico (ej: EasyOCR falló por memoria)
                auditoria.delete()
                messages.error(request, f"Error interno del servidor: {e}")

    else:
        form = CargaForm()
        
    return render(request, 'auditoria/carga.html', {'form': form})

# NUEVA FUNCIÓN: EL DASHBOARD
def dashboard(request):
    # "Select * from Auditoria order by fecha desc"
    registros = Auditoria.objects.all().order_by('-fecha_creacion')
    return render(request, 'auditoria/dashboard.html', {'registros': registros})


def eliminar_auditoria(request, id_auditoria):
    # Buscamos la auditoria por su ID único
    registro = get_object_or_404(Auditoria, pk=id_auditoria)
    
    # 1. Borramos el archivo físico del disco
    if registro.archivo_soat:
        registro.archivo_soat.delete()
    
    # 2. Borramos el registro de la base de datos
    registro.delete()
    
    # 3. Volvemos al dashboard
    return redirect('dashboard')
from django.urls import path
from . import views # Importamos las funciones que acabamos de crear

urlpatterns = [
    # Cuando alguien entre a "nada" (la raíz de auditoria), muéstrale la carga_soportes
    path('', views.carga_soportes, name='carga_soportes'),
    path('dashboard/', views.dashboard, name='dashboard'), # <--- NUEVA RUTA

    # Nueva ruta: recibe un número entero (<int:id_auditoria>)
    path('borrar/<int:id_auditoria>/', views.eliminar_auditoria, name='eliminar_auditoria'),
]
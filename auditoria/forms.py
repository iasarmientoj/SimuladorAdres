from django import forms
from .models import Auditoria

class CargaForm(forms.ModelForm):
    class Meta:
        model = Auditoria
        fields = ['archivo_soat'] # Solo queremos que el usuario suba el archivo
        # Aquí le ponemos estilo "Bootstrap" para que se vea bonito
        widgets = {
            'archivo_soat': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
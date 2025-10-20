from django import forms
from .models import Perfil, CARGO_CHOICES 

class PerfilForm(forms.ModelForm):

    class Meta:
        model = Perfil
        fields = ['nombre', 'apellido' ,'cargo', 'correo']
        

        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'cargo': forms.Select(attrs={'class': 'form-control'}), 
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
        }
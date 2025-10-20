
from django.db import models
from django.contrib.auth.models import User

# Create your models here.
CARGO_CHOICES = [
    ('SELECCIONE', 'Seleccione un cargo'), 
    ('DIRECCION GENERAL', 'Dirección General'),
    ('FINANZAS', 'Finanzas'),
    ('OPERACIONES', 'Operaciones'),
    ('RECURSOS HUMANOS', 'Recursos Humanos'),
    ('MARKETING', 'Marketing'),
    ('TECNOLOGIA', 'Tecnología'),
    ('VENTAS', 'Ventas'),
    ('CONTABILIDAD', 'Contabilidad'),
]

class Perfil(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    cargo = models.CharField(max_length=100 , choices=CARGO_CHOICES, default='SELECCIONE')
    correo = models.EmailField(max_length=254, blank=True, null=True)
    def __str__(self):
      if self.nombre and self.apellido:
        return f"{self.nombre} {self.apellido}"
      elif self.nombre:
        return self.nombre
      elif self.apellido:
        return self.apellido
      else:
       return "Perfil sin nombre"  

class Modulo(models.Model):
    
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    def __str__(self):
        return self.nombre

class Pregunta(models.Model):

    TIPO_CHOICES = [
        ('D', 'Diagnóstico'), 
        ('E', 'Examen de Módulo'),     
    ]
    
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE)
    texto = models.TextField()
    opcion_a = models.CharField(max_length=200)
    opcion_b = models.CharField(max_length=200)
    opcion_c = models.CharField(max_length=200)
    opcion_d = models.CharField(max_length=200)
    respuesta_correcta = models.CharField(max_length=1) 
    
   
    tipo_pregunta = models.CharField(max_length=1, choices=TIPO_CHOICES, default='D') 
    
    def __str__(self):
        return self.texto

class Progreso(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE)
    completado = models.BooleanField(default=False)
    puntaje = models.IntegerField(default=0) # NOTA: Este campo guardará el puntaje del EXAMEN final (o diagnóstico, depende de la última acción).
    def __str__(self):
        return f"{self.user.username} - {self.modulo.nombre}"
    
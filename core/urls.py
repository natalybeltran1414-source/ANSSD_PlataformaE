from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [

    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('perfil/', views.perfil, name='perfil'),
    path('editar_perfil/', views.editar_perfil, name='editar_perfil'),
    path('diagnostico/', views.diagnostico, name='diagnostico'),
    path('modulo/<int:modulo_id>/', views.modulo, name='modulo'),
    path('tutor/', views.tutor, name='tutor'),
    path('progreso/', views.progreso, name='progreso'),
    path('certificado/<int:modulo_id>/', views.generar_certificado, name='certificado'),  
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),  
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),  
    path('modulo/<int:modulo_id>/examen/', views.examen_modulo, name='examen_modulo'),
]
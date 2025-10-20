
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from .models import Perfil, Modulo, Pregunta, Progreso
from .forms import PerfilForm
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from django.contrib import messages 
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, Color
from django.contrib.auth.models import User 
from math import pi, sin


def home(request):
    diagnostico_completado = False
    if request.user.is_authenticated:
        diagnostico_completado = Progreso.objects.filter(user=request.user).exists()
    
    context = {
        'diagnostico_completado': diagnostico_completado 
    }
    
    return render(request, 'core/home.html',context)


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        perfil_form = PerfilForm(request.POST)
        if form.is_valid() and perfil_form.is_valid():
            user = form.save()
            perfil = perfil_form.save(commit=False)
            perfil.user = user
            perfil.save()
            
            messages.success(request, 'Registro Exitoso. Ahora puedes iniciar sesión.')
            return redirect('home')

    else:
        form = UserCreationForm()
        perfil_form = PerfilForm()
    
    previous_url = request.META.get('HTTP_REFERER')
    
    return render(request, 'core/register.html', {
        'form': form, 
        'perfil_form': perfil_form,
        'previous_url': previous_url
    })

@login_required
def perfil(request):
    try:
        perfil_obj = request.user.perfil
        return render(request, 'core/perfil.html', {'perfil': perfil_obj})
        
    except Perfil.DoesNotExist:
        messages.warning(request, 'Por favor, completa tu información de perfil.')
        return redirect('editar_perfil') 

@login_required
def editar_perfil(request):
    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        perfil = Perfil(user=request.user)

    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('perfil')
    else:
        form = PerfilForm(instance=perfil)

    return render(request, 'core/editar_perfil.html', {'form': form})
    
@login_required
def diagnostico(request):
    modulos = Modulo.objects.all()
    #  FILTRO CLAVE: Solo Preguntas de Diagnóstico ('D') 
    preguntas_por_modulo = {modulo: Pregunta.objects.filter(modulo=modulo, tipo_pregunta='D') for modulo in modulos}
    
    if request.method == 'POST':
        brechas = []
        for modulo in modulos:
            #  FILTRO CLAVE: Solo Preguntas de Diagnóstico ('D') 
            preguntas = Pregunta.objects.filter(modulo=modulo, tipo_pregunta='D')
            puntaje = 0
            total_preguntas = len(preguntas)
            for pregunta in preguntas:
                respuesta = request.POST.get(f'pregunta_{pregunta.id}')
                if respuesta and respuesta.upper() == pregunta.respuesta_correcta.upper():
                    puntaje += 1
            
            porcentaje = (puntaje / total_preguntas) * 100 if total_preguntas > 0 else 0
            if porcentaje < 50:  # Umbral del 50% para detectar brechas
                brechas.append(modulo)
            
            progreso, _ = Progreso.objects.get_or_create(user=request.user, modulo=modulo)
            progreso.puntaje = puntaje # Guarda el puntaje del diagnóstico
            progreso.save()
            
        request.session['brechas'] = [m.id for m in brechas]
        return redirect('progreso')
    return render(request, 'core/diagnostico.html', {'preguntas_por_modulo': preguntas_por_modulo})

@login_required
def modulo(request, modulo_id):
    modulo = get_object_or_404(Modulo, id=modulo_id)
    # Se asegura de obtener el progreso para mostrar el estado en la plantilla
    progreso, _ = Progreso.objects.get_or_create(user=request.user, modulo=modulo) 
    
    contenido = {
        'Uso seguro de internet': 'Aprende a proteger tus datos en línea, usar contraseñas seguras y detectar phishing.',
        'Manejo básico de herramientas ofimáticas': 'Domina herramientas como Word, Excel y PowerPoint para el trabajo diario.',
        'Comunicación digital': 'Mejora tus habilidades en correo electrónico, videollamadas y plataformas colaborativas.'
    }.get(modulo.nombre, 'Contenido en desarrollo...')
    
    # La lógica POST para completar se elimina; ahora se hace en el examen
    return render(request, 'core/modulo.html', {'modulo': modulo, 'contenido': contenido, 'progreso': progreso})

# 3. NUEVA FUNCIÓN: examen_modulo (Lógica del examen 7/10)
@login_required
def examen_modulo(request, modulo_id):
    modulo = get_object_or_404(Modulo, id=modulo_id)
    
    # FILTRO CLAVE: Solo Preguntas de Examen ('E') y limitadas a 10 
    preguntas = Pregunta.objects.filter(modulo=modulo, tipo_pregunta='E')[:10] 
    
    progreso, _ = Progreso.objects.get_or_create(user=request.user, modulo=modulo)
    
    if progreso.completado:
        # Si ya aprobó, redirigir a la página del módulo para evitar reintentos
        return redirect('modulo', modulo_id=modulo.id) 

    if request.method == 'POST':
        puntaje = 0
        
        for pregunta in preguntas:

            respuesta_dada = request.POST.get(f'pregunta_{pregunta.id}')
            
            # Comprobación de la respuesta
            if respuesta_dada and respuesta_dada.upper() == pregunta.respuesta_correcta.upper():
                puntaje += 1
        
        # Lógica de Aprobación: Mínimo 7 aciertos de 10
        if puntaje >= 7:
            progreso.completado = True
            mensaje_clase = "alert-success"
            mensaje = f"¡Felicidades! Has aprobado el módulo '{modulo.nombre}' con {puntaje} aciertos. ✨"
        else:
            progreso.completado = False # Asegurar que si reprueba, no se marque como completado
            mensaje_clase = "alert-danger"
            mensaje = f"No has aprobado el módulo '{modulo.nombre}'. Obtuviste *{puntaje}* aciertos. Necesitas 7 o más para aprobar. Inténtalo de nuevo. 😔"
        
        # Guardamos el puntaje del examen. (Sobreescribe el puntaje de diagnóstico)
        progreso.puntaje = puntaje
        progreso.save()
        
        # Guarda el resultado en la sesión para mostrarlo en la vista de progreso
        request.session['examen_resultado'] = {'mensaje': mensaje, 'clase': mensaje_clase}
        return redirect('progreso')
        
    return render(request, 'core/examen_modulo.html', {'modulo': modulo, 'preguntas': preguntas, 'progreso': progreso})

@login_required
def tutor(request):
    respuestas_predefinidas = {
        '¿Qué es seguridad digital?': 'Es el conjunto de prácticas y herramientas para proteger información en línea, como contraseñas seguras y evitar phishing.',
        '¿Cómo usar Excel?': 'Empieza con fórmulas básicas como =SUMA(A1:A10) para sumar celdas.',  
        '¿Cómo redactar un correo profesional?': 'Usa un saludo formal, estructura clara (introducción, cuerpo, cierre) y revisa la ortografía.',
        '¿Qué es phishing?': 'Es un intento fraudulento de obtener información sensible haciéndose pasar por una entidad confiable en una comunicación electrónica.',
        '¿Cómo crear una contraseña segura?': 'Usa una combinación de letras mayúsculas, minúsculas, números y símbolos. Evita palabras comunes y usa al menos 12 caracteres.',
        '¿Qué es una VPN?': 'Una VPN (Red Privada Virtual) cifra tu conexión a internet para proteger tu privacidad y datos en línea.',
        '¿Cómo hacer una presentación efectiva?': 'Usa diapositivas claras, con imágenes relevantes, y practica tu discurso para mantener la atención de la audiencia.',
        '¿Qué es el almacenamiento en la nube?': 'Es un servicio que permite guardar datos en servidores remotos accesibles desde internet, facilitando el acceso y la colaboración.',      
        '¿Cómo evitar el spam en el correo?': 'No compartas tu correo en sitios públicos, usa filtros de spam y no respondas a correos sospechosos.',
        '¿Qué es el software libre?': 'Es software que puede ser usado, modificado y distribuido libremente por cualquier persona.',
        '¿Cómo hacer una copia de seguridad?': 'Usa servicios en la nube o dispositivos externos para guardar copias de tus archivos importantes regularmente.',
        '¿Qué es la autenticación de dos factores?': 'Es un método de seguridad que requiere dos formas de verificación para acceder a una cuenta, como una contraseña y un código enviado a tu teléfono.',
        '¿Cómo mejorar la comunicación en equipo?': 'Usa herramientas colaborativas, establece canales claros de comunicación y fomenta la retroalimentación constructiva.',    
        '¿Qué es un firewall?': 'Es una barrera de seguridad que monitorea y controla el tráfico de red entrante y saliente basado en reglas de seguridad predefinidas.',
        '¿Cómo organizar archivos digitales?': 'Usa carpetas con nombres claros, etiquetas y realiza limpiezas periódicas para eliminar archivos innecesarios.',
        '¿Qué es el teletrabajo?': 'Es la modalidad de trabajo que permite realizar tareas laborales desde cualquier lugar fuera de la oficina, generalmente usando tecnología digital.',   
        '¿Cómo usar PowerPoint?': 'Crea diapositivas con títulos claros, usa listas con viñetas y añade imágenes para hacerlas más atractivas.',
        '¿Qué es el Big Data?': 'Es el manejo y análisis de grandes volúmenes de datos para descubrir patrones, tendencias y asociaciones.',
        '¿Cómo proteger mi privacidad en redes sociales?': 'Ajusta la configuración de privacidad, no compartas información personal y sé selectivo con tus contactos.',
        '¿Qué es el Internet de las Cosas (IoT)?': 'Es la interconexión de dispositivos físicos a internet, permitiendo enviar y recibir datos para mejorar la eficiencia y funcionalidad.',    
        '¿Cómo usar Word?': 'Usa estilos para títulos, revisa la ortografía y aprovecha las plantillas para documentos comunes.',       
        '¿Qué es la inteligencia artificial?': 'Es la simulación de procesos de inteligencia humana por parte de máquinas, especialmente sistemas informáticos.',
        '¿Cómo hacer videollamadas efectivas?': 'Asegúrate de tener buena iluminación, un fondo adecuado y prueba tu equipo antes de la llamada.',  
        '¿Qué es el blockchain?': 'Es una tecnología de registro distribuido que asegura la integridad y transparencia de las transacciones digitales.',
        '¿Cómo gestionar el tiempo usando herramientas digitales?': 'Usa calendarios en línea, aplicaciones de tareas y establece recordatorios para mantenerte organizado.',   
        '¿Qué es el machine learning?': 'Es una rama de la inteligencia artificial que permite a las máquinas aprender de los datos y mejorar su rendimiento sin ser programadas explícitamente.',      
        '¿Cómo colaborar en documentos en línea?': 'Usa plataformas como Google Docs o Microsoft OneDrive que permiten la edición simultánea y comentarios en tiempo real.',
        '¿Qué es la realidad aumentada?': 'Es una tecnología que superpone información digital (imágenes, sonidos) en el mundo real a través de dispositivos como smartphones o gafas especiales.',
        '¿Cómo mantener mi computadora segura?': 'Mantén tu software actualizado, usa antivirus y evita descargar archivos de fuentes no confiables.',
        '¿Qué es el SaaS (Software como Servicio)?': 'Es un modelo de distribución de software donde las aplicaciones se alojan en la nube y se accede a ellas a través de internet.',
        '¿Cómo usar herramientas de gestión de proyectos?': 'Utiliza plataformas como Trello o Asana para organizar tareas, asignar responsabilidades y seguir el progreso del equipo.',
        '¿Qué es la computación en la nube?': 'Es el uso de servidores remotos en internet para almacenar, gestionar y procesar datos, en lugar de hacerlo en un servidor local o una computadora personal.',
        '¿Cómo hacer búsquedas efectivas en internet?': 'Usa palabras clave específicas, comillas para frases exactas y operadores como AND, OR para refinar resultados.',
        '¿Qué es el desarrollo web?': 'Es la creación y mantenimiento de sitios web, que incluye aspectos como diseño, contenido y funcionalidad.',
        '¿Cómo proteger mis dispositivos móviles?': 'Usa contraseñas, activa la autenticación de dos factores y evita conectarte a redes Wi-Fi públicas sin protección.',
        '¿Qué es la ciberseguridad?': 'Es la práctica de proteger sistemas, redes y programas de ataques digitales para salvaguardar la información y la privacidad.'
    }
    respuesta = None
    if request.method == 'POST':
        pregunta = request.POST.get('pregunta')
        respuesta = respuestas_predefinidas.get(pregunta, 'Lo siento, no tengo una respuesta para esa pregunta. Intenta con otra.')
    return render(request, 'core/tutor.html', {'respuesta': respuesta, 'preguntas': respuestas_predefinidas.keys()})



@login_required
def progreso(request):
    # 1. Obtener todos los progresos del usuario ordenados
    progresos = Progreso.objects.filter(user=request.user).order_by('modulo__id')
    
    modulos_completados = progresos.filter(completado=True)
    completados_count = modulos_completados.count()
    total = progresos.count()  # Cuenta solo los módulos existentes para este usuario en Progreso
    
    # 2. Calcular Porcentaje Real
    porcentaje_real = round((completados_count / total) * 100) if total > 0 else 0

    # 3. Obtener TODOS los módulos pendientes (Opción 2)
    modulos_pendientes = progresos.filter(completado=False).order_by('modulo__id')
    
    # 4. Obtener y limpiar el mensaje de resultado del examen
    mensaje_resultado = request.session.pop('examen_resultado', None) 
    
    return render(request, 'core/progreso.html', {
        'progresos': progresos,
        'completados': completados_count,
        'total': total,
        'porcentaje_real': porcentaje_real,
        'modulos_pendientes': modulos_pendientes,  
        'mensaje_resultado': mensaje_resultado
    })


@login_required
def generar_certificado(request, modulo_id):
    # Verifica si el módulo está completado para este usuario
    progreso = get_object_or_404(Progreso, user=request.user, modulo_id=modulo_id)
    if not progreso.completado:
        return redirect('progreso')

    # Obtener detalles del módulo
    modulo = progreso.modulo

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificado_{modulo.nombre}_{request.user.username}.pdf"'

    p = canvas.Canvas(response, pagesize=landscape(A4))
    width, height = landscape(A4)

    # --- FONDO LIMPIO ---
    p.setFillColor(HexColor("#FFFFFF"))
    p.rect(0, 0, width, height, fill=1)
    
    # --- BORDE ELEGANTE ---
    margin = 0.6 * inch
    p.setStrokeColor(HexColor("#2C5F9B"))
    p.setLineWidth(6)
    p.rect(margin, margin, width-2*margin, height-2*margin, stroke=1, fill=0)

    # --- LOGOTIPO  EN ESQUINA SUPERIOR DERECHA ---
    logo_x = width - margin - 1.2*inch  # Posición X para el logo
    logo_y = height - margin - 0.8*inch  # Posición Y para el logo
    
    #  logo 
    p.setLineWidth(0.15*inch)
    p.setLineCap(1)
    segments = 100
    w = 0.8 * inch
    amp = 0.2 * inch
    freq = 1
    phase = 3 * pi / 2
    start_x = logo_x - 0.4 * inch
    start_color = Color(54/255, 209/255, 220/255)  # Azul
    end_color = Color(255/255, 94/255, 98/255)  # Rosa
    
    for i in range(segments):
        t1 = i / segments
        t2 = (i + 1) / segments
        y1 = logo_y + amp * sin(2 * pi * freq * t1 + phase)
        x1 = start_x + w * t1
        y2 = logo_y + amp * sin(2 * pi * freq * t2 + phase)
        x2 = start_x + w * t2
        fraction = (t1 + t2) / 2
        r = start_color.red + fraction * (end_color.red - start_color.red)
        g = start_color.green + fraction * (end_color.green - start_color.green)
        b = start_color.blue + fraction * (end_color.blue - start_color.blue)
        color = Color(r, g, b)
        p.setStrokeColor(color)
        p.line(x1, y1, x2, y2)
    
    # Texto ANSSD debajo del logo
    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(HexColor("#2C5F9B"))
    p.drawCentredString(logo_x, logo_y - 0.7*inch, "ANSSD")

    # --- ENCABEZADO ---
    
    # Título principal
    p.setFont("Helvetica-Bold", 24)
    p.setFillColor(HexColor("#1A365D"))
    p.drawCentredString(width/2, height-1.8*inch, "CERTIFICADO DE PARTICIPACIÓN")
    
    # Línea decorativa bajo el título
    p.setStrokeColor(HexColor("#E6A23C"))
    p.setLineWidth(2)
    p.line(width/2-1.6*inch, height-2.0*inch, width/2+1.6*inch, height-2.0*inch)

    # --- CONTENIDO PRINCIPAL ---
    
    # Texto de presentación
    p.setFont("Helvetica", 13)
    p.setFillColor(HexColor("#555555"))
    p.drawCentredString(width/2, height-2.6*inch, "Se otorga el presente certificado a:")

    # Nombre completo del usuario (nombre + apellido)
    p.setFont("Helvetica-Bold", 28)
    p.setFillColor(HexColor("#2C5F9B"))

    try:
      perfil = request.user.perfil
      nombre_completo = f"{perfil.nombre.upper()} {perfil.apellido.upper()}"
    except:
      nombre_completo = request.user.get_full_name().upper() or request.user.username.upper()

    p.drawCentredString(width/2, height-3.3*inch, nombre_completo)

    # Texto de reconocimiento
    p.setFont("Helvetica", 12)
    p.setFillColor(HexColor("#666666"))
    p.drawCentredString(width/2, height-3.9*inch, "Por haber completado exitosamente el")
    
    # Nombre del módulo
    p.setFont("Helvetica-Bold", 16)
    p.setFillColor(HexColor("#1A365D"))
    p.drawCentredString(width/2, height-4.4*inch, f"MÓDULO DE {modulo.nombre.upper()}")
    
    # Texto adicional
    p.setFont("Helvetica", 11)
    p.setFillColor(HexColor("#777777"))
    p.drawCentredString(width/2, height-4.9*inch, "demostrando competencia y dedicación en el aprendizaje")

    # --- SECCIÓN INFERIOR: FIRMA Y FECHA ---
    y_base = height - 6.0*inch
    
    # Línea separadora
    p.setStrokeColor(HexColor("#CBD5E0"))
    p.setLineWidth(0.5)
    p.line(2*inch, y_base, width-2*inch, y_base)

    # FECHA (Izquierda)
    x_fecha = 3 * inch
    
    p.setFont("Helvetica-Bold", 11)
    p.setFillColor(HexColor("#2C5F9B"))
    p.drawCentredString(x_fecha, y_base - 0.6*inch, "Fecha de Emisión")
    
    p.setFont("Helvetica", 11)
    p.setFillColor(HexColor("#1A365D"))
    
    # Formatear fecha en español
    meses_es = {
        'January': 'enero', 'February': 'febrero', 'March': 'marzo',
        'April': 'abril', 'May': 'mayo', 'June': 'junio',
        'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
        'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
    }
    fecha_emision = request.user.date_joined
    mes_es = meses_es.get(fecha_emision.strftime('%B'), fecha_emision.strftime('%B'))
    fecha_formateada = f"{fecha_emision.strftime('%d')} de {mes_es} de {fecha_emision.strftime('%Y')}"
    
    p.drawCentredString(x_fecha, y_base - 0.9*inch, fecha_formateada)

    # FIRMA (Derecha)
    x_firma = width - 3 * inch
    
    # FIRMA GRÁFICA
    p.setStrokeColor(HexColor("#2C5F9B"))
    p.setLineWidth(1.8)
    
    # Dibujar firma
    signature_points = [
        (x_firma-1.2*inch, y_base - 0.5*inch),
        (x_firma-0.9*inch, y_base - 0.4*inch),
        (x_firma-0.6*inch, y_base - 0.6*inch),
        (x_firma-0.3*inch, y_base - 0.35*inch),
        (x_firma, y_base - 0.55*inch),
        (x_firma+0.3*inch, y_base - 0.4*inch),
        (x_firma+0.6*inch, y_base - 0.65*inch),
        (x_firma+0.9*inch, y_base - 0.45*inch)
    ]
    
    for i in range(len(signature_points)-1):
        p.line(signature_points[i][0], signature_points[i][1],
               signature_points[i+1][0], signature_points[i+1][1])
    
    # Línea de firma
    p.setStrokeColor(HexColor("#2C5F9B"))
    p.setLineWidth(1)
    p.line(x_firma-1.0*inch, y_base - 0.7*inch, x_firma+1.0*inch, y_base - 0.7*inch)

    # Información del firmante
    p.setFont("Helvetica-Bold", 11)
    p.setFillColor(HexColor("#2C5F9B"))
    p.drawCentredString(x_firma, y_base - 0.9*inch, "Ing. Elena Mendoza")
    
    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(HexColor("#666666"))
    p.drawCentredString(x_firma, y_base - 1.1*inch, "Coordinadora de Formación Digital ANSSD")

    # --- CÓDIGO DE VERIFICACIÓN ---
    codigo_verificacion = f"CÓDIGO DE VERIFICACIÓN: CD-{request.user.id:06d}-{modulo.id:03d}-{request.user.date_joined.strftime('%Y%m')}"
    
    p.setFont("Helvetica", 8)
    p.setFillColor(HexColor("#666666"))
    p.drawCentredString(width/2, margin + 0.2*inch, codigo_verificacion)

    # --- ELEMENTOS DECORATIVOS ---
    p.setStrokeColor(HexColor("#E6A23C"))
    p.setLineWidth(1)
    
    # Pequeños adornos en esquinas (solo esquina superior izquierda ahora)
    corner_size = 0.2 * inch
    # Esquina superior izquierda
    p.line(margin, height-margin-corner_size, margin, height-margin)
    p.line(margin, height-margin, margin+corner_size, height-margin)

    p.showPage()
    p.save()
    return response
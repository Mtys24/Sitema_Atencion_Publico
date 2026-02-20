from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

# Create your views here.

from .models import Funcionario, ModuloAtencion, TipoAtencion, Ticket, Cliente
from django.db.models import Max
from django.utils import timezone
from datetime import date
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db import connections
import re


def inicio(request):
    tipos = TipoAtencion.objects.all()
    return render(request, 'inicio.html',{'tipos':tipos})

def ingresar_rut(request, tipo_id):
    tipo= get_object_or_404(TipoAtencion, id=tipo_id)
    return render(request, 'ingresar_rut.html',{'tipo':tipo})

import re

def validar_rut(rut):
    rut = rut.upper()
    rut = re.sub(r'[^0-9K]', '', rut)

    if len(rut) < 8:
        return False

    cuerpo = rut[:-1]
    dv = rut[-1]

    try:
        int(cuerpo)
    except ValueError:
        return False

    suma = 0
    multiplo = 2

    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo = multiplo + 1 if multiplo < 7 else 2

    resto = 11 - (suma % 11)

    if resto == 11:
        dv_calculado = '0'
    elif resto == 10:
        dv_calculado = 'K'
    else:
        dv_calculado = str(resto)

    return dv == dv_calculado

from datetime import date, timedelta

def generar_ticket(request, tipo_id):
    tipo = get_object_or_404(TipoAtencion, id=tipo_id)

    if request.method == "POST":
        rut = request.POST.get("rut", "").upper().replace(".", "").replace("-", "")
        
        if not validar_rut(rut):
            messages.error(request, "RUT inválido")
            return redirect("ingresar_rut", tipo_id=tipo.id)

        cliente, created = Cliente.objects.get_or_create(
            rut=rut,
            defaults={
                "nombre": "Vecino",
                "apellido_paterno": "Santa Cruz",
                "apellido_materno": "",
                "fecha_nacimiento": date(2000, 1, 1), 
                "discapacidad": False,
            }
        )
        
        es_prioritario = tipo.letra == 'L' 

        ultimo_ticket = Ticket.objects.filter(tipo_atencion=tipo).aggregate(Max("numero"))
        ultimo_numero = ultimo_ticket["numero__max"]
        correlativo = int(ultimo_numero[1:]) + 1 if ultimo_numero else 1
        numero_ticket = f"{tipo.letra}{correlativo:03d}"

        ticket = Ticket.objects.create(
            numero=numero_ticket,
            cliente=cliente,
            tipo_atencion=tipo,
            estado='EN_COLA'
        )

        return render(request, "ticket_generado.html", {
            "ticket": ticket,
            "es_adulto_mayor": es_prioritario,
        })

    return redirect("inicio")



def tablero_turnos(request):
    hoy = date.today()

    tickets_en_cola = Ticket.objects.filter(estado='EN_COLA').select_related('cliente', 'tipo_atencion')

    tickets_en_atencion = Ticket.objects.filter(estado='EN_ATENCION').select_related('cliente', 'tipo_atencion')

    tickets_atendidos = Ticket.objects.filter(estado='ATENDIDO').order_by('-fecha_emision')[:10].select_related('cliente', 'tipo_atencion')

    prioritarios = []
    normales = []

    for ticket in tickets_en_cola:
        cliente = ticket.cliente

        edad = hoy.year - cliente.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (cliente.fecha_nacimiento.month, cliente.fecha_nacimiento.day)
        )

        if edad >= 60 or cliente.discapacidad:
            prioritarios.append(ticket)
        else:
            normales.append(ticket)

    context = {
        "prioritarios": prioritarios,
        "normales": normales,
        "en_atencion": tickets_en_atencion,
        "atendidos": tickets_atendidos,
    }

    return render(request, "tablero_turnos.html", context)



def api_tablero(request):
    hoy = date.today()

    # 1. EN COLA: Ordenamos por fecha de emisión para mantener el orden de llegada
    tickets_en_cola = Ticket.objects.filter(
        estado="EN_COLA"
    ).select_related("cliente", "tipo_atencion").order_by("fecha_emision")

    # 2. EN ATENCION: ¡CRÍTICO! Ordenamos por ID para que el JS detecte siempre el último
    tickets_en_atencion = Ticket.objects.filter(
        estado="EN_ATENCION"
    ).select_related("tipo_atencion", "funcionario__modulo").order_by("id")

    # 3. ATENDIDOS: Los últimos 5 que ya terminaron
    tickets_atendidos = Ticket.objects.filter(
        estado="ATENDIDO"
    ).select_related("tipo_atencion", "funcionario__modulo").order_by("-fecha_emision")[:5]

    en_cola = []
    en_atencion = []
    atendidos = []

    # Procesar EN COLA
    for ticket in tickets_en_cola:
        cliente = ticket.cliente
        # Cálculo de edad simplificado
        edad = hoy.year - cliente.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (cliente.fecha_nacimiento.month, cliente.fecha_nacimiento.day)
        )
        prioridad = cliente.discapacidad or edad >= 60
        
        en_cola.append({
            "numero": ticket.numero,
            "prioridad": prioridad,
            "tramite": ticket.tipo_atencion.nombre if ticket.tipo_atencion else "General"
        })

    # Procesar EN ATENCION
    for ticket in tickets_en_atencion:
        modulo_numero = ticket.funcionario.modulo.numero if (ticket.funcionario and ticket.funcionario.modulo) else "?"
        
        en_atencion.append({
            "id": ticket.id,         # VITAL para que el JS sepa que es nuevo
            "numero": ticket.numero,
            "modulo": modulo_numero,
            "tramite": ticket.tipo_atencion.nombre if ticket.tipo_atencion else "General"
        })

    # Procesar ATENDIDOS
    for ticket in tickets_atendidos:
        modulo_numero = ticket.funcionario.modulo.numero if (ticket.funcionario and ticket.funcionario.modulo) else "?"
        
        atendidos.append({
            "numero": ticket.numero,
            "modulo": modulo_numero,
            "tramite": ticket.tipo_atencion.nombre if ticket.tipo_atencion else "General"
        })

    return JsonResponse({
        "en_cola": en_cola,
        "en_atencion": en_atencion,
        "atendidos": atendidos
    })


def login_funcionario(request):
    modulos = ModuloAtencion.objects.all()

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        modulo_id = request.POST.get("modulo")

        try:
            funcionario = Funcionario.objects.get(email=email)
        except Funcionario.DoesNotExist:
            messages.error(request, "Funcionario no encontrado")
            return redirect("login_funcionario")

        if funcionario.estado != "ACTIVO":
            messages.error(request, "Funcionario no habilitado")
            return redirect("login_funcionario")

        if funcionario.password != password:
            messages.error(request, "Contraseña incorrecta")
            return redirect("login_funcionario")

        modulo = get_object_or_404(ModuloAtencion, id=modulo_id)

        modulo_ocupado = Funcionario.objects.filter(
            modulo=modulo,
            estado="ACTIVO"
        ).exclude(id=funcionario.id).exists()

        if modulo_ocupado:
            messages.error(request, "Este módulo ya está en uso. Elija otro.")
            return redirect("login_funcionario")

        funcionario.modulo = modulo
        funcionario.save()

        request.session["funcionario_id"] = funcionario.id
        request.session["modulo_id"] = modulo.id

        return redirect("panel_funcionario")

    return render(request, "login_funcionario.html", {"modulos": modulos})


def panel_funcionario(request):
    funcionario_id = request.session.get("funcionario_id")
    if not funcionario_id:
        return redirect("login_funcionario")

    funcionario = Funcionario.objects.get(id=funcionario_id)
    hoy = date.today()
    tickets = Ticket.objects.filter(
        estado__in=["EN_COLA", "EN_ATENCION"]
    ).select_related("cliente", "tipo_atencion", "funcionario")

    lista_tickets = []
    for ticket in tickets:
        cliente = ticket.cliente
        edad = hoy.year - cliente.fecha_nacimiento.year - ((hoy.month, hoy.day) < (cliente.fecha_nacimiento.month, cliente.fecha_nacimiento.day))
        prioridad = cliente.discapacidad or edad >= 60

        lista_tickets.append({
            "id": ticket.id,
            "numero": ticket.numero,
            "nombre": f"{cliente.nombre} {cliente.apellido_paterno}",
            "tipo": ticket.tipo_atencion.nombre,
            "prioridad": prioridad,
            "en_uso": ticket.estado == "EN_ATENCION",
            "funcionario": ticket.funcionario.nombre if ticket.funcionario else None
        })

    ticket_en_atencion = Ticket.objects.filter(estado="EN_ATENCION", funcionario=funcionario).first()

    ultimos_atendidos = Ticket.objects.filter(funcionario=funcionario, estado="ATENDIDO").order_by("-fecha_emision")[:5]

    return render(request, "panel_funcionario.html", {
        "funcionario": funcionario,
        "tickets": lista_tickets,
        "ticket_en_atencion": ticket_en_atencion,
        "ultimos_atendidos": ultimos_atendidos
    })



def logout_funcionario(request):
    funcionario_id = request.session.get("funcionario_id")

    if funcionario_id:
        funcionario = Funcionario.objects.get(id=funcionario_id)
        funcionario.modulo = None
        funcionario.save()

    request.session.flush()
    return redirect("login_funcionario")


@require_POST
def llamar_ticket(request, ticket_id):
    funcionario_id = request.session.get("funcionario_id")
    if not funcionario_id:
        return JsonResponse({"success": False, "error": "No autenticado"})

    funcionario = Funcionario.objects.get(id=funcionario_id)

    if Ticket.objects.filter(funcionario=funcionario, estado="EN_ATENCION").exists():
        return JsonResponse({"success": False, "error": "Ya tiene un ticket en atención"})

    try:
        with transaction.atomic():

            ticket = Ticket.objects.select_for_update().get(id=ticket_id)

            if ticket.estado != "EN_COLA":
                return JsonResponse({"success": False, "error": "Ticket ya fue tomado por otro funcionario"})

            ticket.estado = "EN_ATENCION"
            ticket.funcionario = funcionario
            ticket.save()

    except Ticket.DoesNotExist:
        return JsonResponse({"success": False, "error": "Ticket no existe"})

    return JsonResponse({"success": True})



@require_POST
def finalizar_ticket(request, ticket_id):
    funcionario_id = request.session.get("funcionario_id")
    if not funcionario_id:
        return JsonResponse({"success": False})

    funcionario = Funcionario.objects.get(id=funcionario_id)

    try:
        with transaction.atomic():
            ticket = Ticket.objects.select_for_update().get(
                id=ticket_id,
                funcionario=funcionario,
                estado="EN_ATENCION"
            )

            ticket.estado = "ATENDIDO"
            ticket.save()

    except Ticket.DoesNotExist:
        return JsonResponse({"success": False, "error": "Ticket inválido"})

    return JsonResponse({"success": True})



def api_panel(request):
    funcionario_id = request.session.get("funcionario_id")
    if not funcionario_id:
        return JsonResponse({})

    funcionario = Funcionario.objects.get(id=funcionario_id)
    
    tickets = Ticket.objects.filter(estado="EN_COLA").select_related("cliente", "tipo_atencion")

    lista = []
    for t in tickets:
        es_licencia = t.tipo_atencion.letra == 'L' or "LICENCIA" in t.tipo_atencion.nombre.upper()
        
        prioridad = es_licencia

        lista.append({
            "id": t.id,
            "numero": t.numero,
            "nombre": f"{t.cliente.nombre} {t.cliente.apellido_paterno}",
            "rut": t.cliente.rut,
            "tipo": t.tipo_atencion.nombre,
            "prioridad": prioridad,
        })

    ticket_en_atencion = Ticket.objects.filter(
        estado="EN_ATENCION",
        funcionario=funcionario
    ).select_related("cliente", "tipo_atencion").first()

    if ticket_en_atencion:
        en_atencion = {
            "id": ticket_en_atencion.id,
            "numero": ticket_en_atencion.numero,
            "nombre": f"{ticket_en_atencion.cliente.nombre} {ticket_en_atencion.cliente.apellido_paterno}",
            "rut": ticket_en_atencion.cliente.rut,
            "tipo": ticket_en_atencion.tipo_atencion.nombre,
        }
    else:
        en_atencion = {}

    ultimos = Ticket.objects.filter(
        funcionario=funcionario,
        estado="ATENDIDO"
    ).order_by("-fecha_emision")[:5]

    ultimos_atendidos = [
        {
            "numero": t.numero,
            "nombre": f"{t.cliente.nombre} {t.cliente.apellido_paterno}"
        }
        for t in ultimos
    ]

    return JsonResponse({
        "tickets": lista,
        "en_atencion": en_atencion,
        "ultimos_atendidos": ultimos_atendidos
    })
from django.contrib import admin

# Register your models here.

from .models import Cliente, TipoAtencion, ModuloAtencion, Funcionario, Ticket


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display= ('rut','nombre','apellido_paterno','apellido_materno','discapacidad')
    search_fields= ('rut', 'nombre', 'apellido_paterno')
    list_filter=('discapacidad',)

@admin.register(TipoAtencion)
class TipoAtencionAdmin(admin.ModelAdmin):
    list_display =('letra','nombre')
    search_fields=('letra','nombre')

@admin.register(ModuloAtencion)
class ModuloAtencionAdmin(admin.ModelAdmin):
    list_display=('numero',)

@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display=('email','nombre','apellido_paterno','estado','modulo')
    search_fields=('email','nombre', 'apellido_paterno')
    list_filter=('estado','modulo')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display=('numero','estado','tipo_atencion','cliente','funcionario','fecha_emision')
    search_fields=('numero','cliente__rut')
    list_filter=('estado','tipo_atencion','fecha_emision')
from django.urls import path
from . import views


urlpatterns = [
    path('',views.inicio, name="inicio"),
    path('tipo/<int:tipo_id>/', views.ingresar_rut, name='ingresar_rut'),
    path('generar-ticket/<int:tipo_id>/', views.generar_ticket, name='generar_ticket'),
    path('tablero/', views.tablero_turnos, name='tablero_turnos'),
    path('api-tablero/', views.api_tablero, name='api_tablero'),
    path("login/", views.login_funcionario, name="login_funcionario"),
    path("logout/", views.logout_funcionario, name="logout_funcionario"),
    path("panel/", views.panel_funcionario, name="panel_funcionario"),
    path("llamar/<int:ticket_id>/", views.llamar_ticket),
    path("finalizar/<int:ticket_id>/", views.finalizar_ticket),
    path("api-panel/", views.api_panel),
]

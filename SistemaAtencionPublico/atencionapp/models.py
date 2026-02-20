from django.db import models


class Cliente(models.Model):
    rut = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=50)
    apellido_paterno = models.CharField(max_length=50)
    apellido_materno = models.CharField(max_length=50)
    fecha_nacimiento = models.DateField()
    discapacidad = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno}"


class TipoAtencion(models.Model):
    nombre = models.CharField(max_length=100)
    letra = models.CharField(max_length=5, unique=True)

    def __str__(self):
        return f"{self.letra} - {self.nombre}"


class ModuloAtencion(models.Model):
    numero = models.IntegerField(unique=True)

    def __str__(self):
        return f"Módulo {self.numero}"


class Funcionario(models.Model):
    ESTADOS = [('ACTIVO', 'Activo'),('DESACTIVADO', 'Desactivado'),('DESHABILITADO', 'Deshabilitado'),]
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=50)
    apellido_paterno = models.CharField(max_length=50)
    apellido_materno = models.CharField(max_length=50)
    password = models.CharField(max_length=100)
    modulo = models.ForeignKey(ModuloAtencion,on_delete=models.SET_NULL, null=True, blank=True)
    estado = models.CharField(max_length=20,choices=ESTADOS,default='ACTIVO')

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno}"


class Ticket(models.Model):
    ESTADOS = [('EN_COLA', 'En cola'),('EN_ATENCION', 'En atención'),('ATENDIDO', 'Atendido'),]
    numero = models.CharField(max_length=10, unique=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='EN_COLA')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='tickets')
    tipo_atencion = models.ForeignKey(TipoAtencion, on_delete=models.CASCADE, related_name='tickets')
    funcionario = models.ForeignKey(Funcionario, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')

    def __str__(self):
        return f"{self.numero} - {self.estado}"
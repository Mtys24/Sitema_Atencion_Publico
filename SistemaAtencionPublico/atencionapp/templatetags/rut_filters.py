from django import template

register = template.Library()

@register.filter
def format_rut(value):
    """
    Formatea un RUT chileno.
    Ej: 12345678K -> 12.345.678-K
    """
    if not value:
        return ""
    value = str(value).replace(".", "").replace("-", "")
    cuerpo = value[:-1]
    dv = value[-1]
    cuerpo = '.'.join([cuerpo[max(i-3,0):i] for i in range(len(cuerpo), 0, -3)][::-1])
    return f"{cuerpo}-{dv}"

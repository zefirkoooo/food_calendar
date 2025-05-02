from django import template

register = template.Library()

@register.filter(name='get_field_value')
def get_field_value(form, field_name):
    """
    Get the value of a form field by name
    """
    if not form:
        return None
    
    try:
        field = form.fields.get(field_name)
        if not field:
            return None
            
        if hasattr(form, 'cleaned_data'):
            return form.cleaned_data.get(field_name)
        elif form.data:
            return form.data.get(field_name)
    except AttributeError:
        return None
        
    return None 

@register.filter
def getattr(obj, attr):
    """
    Получает значение атрибута объекта.
    Использование: {{ object|getattr:"attribute_name" }}
    """
    try:
        return getattr(obj, attr)
    except (AttributeError, TypeError):
        return None 
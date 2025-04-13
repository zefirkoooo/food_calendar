from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def add_str(arg1, arg2):
    return str(arg1) + str(arg2)

@register.simple_tag
def selected_dish(form, dish_id, user_id, day_id):
    field_name = f'dish_{dish_id}'
    if field_name in form.initial:
        return form.initial[field_name]
    return False
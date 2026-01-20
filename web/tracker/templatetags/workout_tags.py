from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key in templates"""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.simple_tag
def workout_type_color(workout_type):
    """Return color class for workout type"""
    colors = {
        "weightlifting": "purple",
        "cardio": "cyan",
        "hiit": "orange",
    }
    return colors.get(workout_type, "indigo")

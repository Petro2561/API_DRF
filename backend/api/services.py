from rest_framework.serializers import ValidationError

from recipes.models import AmountIngredient


def check_value_validate(value, klass=None):
    """Проверяет корректность переданного значения.
    Если передан класс, проверяет существует ли объект с переданным obj_id.
    При нахождении объекта создаётся Queryset[],
    для дальнейшей работы возвращается первое (и единственное) значение.
    Args:
        value (int, str):
            Значение, переданное для проверки.
        klass(class):
            Если значение передано, проверяет наличие объекта с id=value.
    Returns:
        None:
            Если переданно только корректно значение.
        obj:
            Объект переданного класса, если дополнительно указан класс.
    Raises:
        ValidationError:
            Переданное значение не является числом.
        ValidationError:
            Объекта с указанным id не существует.
    """
    if klass:
        obj = klass.objects.filter(id=value)
        if not obj:
            raise ValidationError(
                f'{value} не существует'
            )
        return obj[0]
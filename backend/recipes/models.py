from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()


class Ingredient(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name='Ингридиент'
    )
    measurument_unit = models.CharField(
        max_length=200,
        verbose_name='Единица измерения'
    )

    class Meta:
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Ингридиенты'

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name='Тег'
    )
    color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        verbose_name='Цвет в HEX',
        unique=True
    )
    slug = models.SlugField(
        blank=True,
        max_length=200,
        unique=True
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    tags = models.ManyToManyField(
        Tag,
        related_name='reciepes',
        verbose_name='Тег'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        related_name='recipes',
        verbose_name='Ингридиенты',
        through='AmountIngredient'
    )
    favorite = models.ManyToManyField(
        User,
        related_name='favorites',
        verbose_name='Понравившиеся рецепты',
        blank=True
    )
    shopping_cart = models.ManyToManyField(
        User,
        related_name='carts',
        verbose_name='Список покупок',
        blank=True
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Имя'
    )
    image = models.ImageField(
        upload_to='recipes/images',
        verbose_name='Фото рецепта'
    )
    text = models.TextField(
        verbose_name='Описание рецепта'
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления в минутах',
        validators=(
            MinValueValidator(
                1,
                'Поставьте корректное время приготовления!'
            ),
        )
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class AmountIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        related_name='recipe',
        on_delete=models.CASCADE,
        verbose_name='Ингридиенты'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        related_name='ingredient',
        on_delete=models.CASCADE,
        verbose_name='Ингридиенты'
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество ингридиента',
        validators=(
            MinValueValidator(
                1,
                'Недостаточно ингридиента'
            ),
        )
    )

    class Meta:
        verbose_name = 'Количество Ингридиентa'
        verbose_name_plural = 'Количество Ингридиентов'

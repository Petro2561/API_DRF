from django.contrib.auth import get_user_model
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import Ingredient, Recipe, Tag

User = get_user_model()


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurument_unit')


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class AmountIngredientSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurument_unit', 'amount')

    def get_amount(self, obj):
        return obj.ingredient.values('amount')[0]['amount']


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.subscribed.filter(id=obj.id).exists()


class RecipeSerializer(serializers.ModelSerializer):
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    tags = TagSerializer(many=True)
    ingredients = AmountIngredientSerializer(many=True)
    author = UserSerializer()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.favorites.filter(id=obj.id).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.carts.filter(id=obj.id).exists()


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    ingredients = AmountIngredientSerializer(
        many=True,
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
        )
        read_only_fields = ('author',)

    def validate(self, data):
        ingredients = data.get('ingredients')
        tags = data.get('tags')
        cooking_time = data.get('cooking_time')
        if len(ingredients) == 0:
            raise serializers.ValidationError(
                'Необходимо указать ингредиенты для рецепта.'
            )
        set_ingr = set()
        for ingredient in ingredients:
            ingredient = ingredient.get('id')
            if ingredient in set_ingr:
                raise serializers.ValidationError(
                    'В рецепте не может быть нескольких одинаковых '
                    'ингредиентов.'
                )
            set_ingr.add(ingredient)
        if len(tags) == 0:
            raise serializers.ValidationError('Укажите теги рецепта')

        for tag in tags:
            if tag not in Tag.objects.all():
                raise serializers.ValidationError(
                    'Такого тега не существует!'
                )
        if cooking_time <= 0:
            raise serializers.ValidationError(
                'Время приготовления не может быть 0 или меньше.'
            )
        return data

    def add_ingredients(self, instance, ingrs_data):
        for ingredients in ingrs_data:
            ingridient, amount = ingredients.values()
            through = AmountIngredientSerializer(
                recipe=instance,
                ingredients=ingridient,
                amount=amount,
            )
            through.save()
        return instance


class UserCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password'
        )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class UserRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class UserSubscribtionsSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'recipes', 'recipes_count')

    def get_recipes(self, obj):
        recipes_limit = self.context.get(
            'request').query_params.get('recipes_limit')
        if recipes_limit:
            if not recipes_limit.isdigit():
                message = 'Параметр recipes_limit должен быть числом'
                raise serializers.ValidationError(message)
            recipes_limit = int(recipes_limit)
            if recipes_limit < 0:
                message = 'Параметр recipes_limit должен быть больше 0'
                raise serializers.ValidationError(message)

        serializer = UserRecipeSerializer(
            obj.recipes.all()[:recipes_limit],
            many=True,
        )
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

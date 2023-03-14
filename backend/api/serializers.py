from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.serializers import \
    UserCreateSerializer as DjoserUserCreateSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.serializers import (ModelSerializer, SerializerMethodField,
                                        ValidationError)
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import AmountIngredient, Ingredient, Recipe, Tag

User = get_user_model()


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurument_unit')


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = "__all__"


class AmountIngredientSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurument_unit', 'amount')

    def get_amount(self, obj):
        return obj.ingredient.values('amount')[0]['amount']


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed')


class RecipeSerializer(serializers.ModelSerializer):
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)
    tags = TagSerializer(many=True)
    ingredients = AmountIngredientSerializer(many=True)
    author = UserSerializer()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')
        validators = [
            UniqueTogetherValidator(
                queryset=Recipe.objects.all(),
                fields=['is_favorited', 'author'],
                message=('Нельзя подписаться на свой рецепт')
            )
        ]

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

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('ingredients')
        image = validated_data.pop('image')
        recipe = Recipe.objects.create(image=image, **validated_data)
        for ingredient in ingredients:
            AmountIngredient.objects.get_or_create(
                recipe=recipe,
                ingredients=ingredient['ingredient'],
                amount=ingredient['amount']
            )
        recipe.tags.set(tags)
        return recipe

    def update(self, recipe, validated_data):
        tags = validated_data.get('tags')
        ingredients = validated_data.get('ingredients')

        recipe.image = validated_data.get(
            'image', recipe.image)
        recipe.name = validated_data.get(
            'name', recipe.name)
        recipe.text = validated_data.get(
            'text', recipe.text)
        recipe.cooking_time = validated_data.get(
            'cooking_time', recipe.cooking_time)

        if tags:
            recipe.tags.clear()
            recipe.tags.set(tags)

        if ingredients:
            recipe.ingredients.clear()
            for ingredient in ingredients:
                AmountIngredient.objects.get_or_create(
                    recipe=recipe,
                    ingredients=ingredient['ingredient'],
                    amount=ingredient['amount']
                )
        recipe.save()
        return recipe


class UserCreateSerializer(DjoserUserCreateSerializer):
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


class FavoriteRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('pk',)

    def validate(self, data):
        request = self.context.get('request')
        pk = data.get('pk')
        obj = get_object_or_404(Recipe, id=pk)
        user = self.context.get('request').user
        favorite_exist = Recipe.objects.filter(favorite=user).exists()
        if request.method == 'POST':
            if obj.author == user:
                raise ValidationError('Нельзя добавить свой рецепт')
            if favorite_exist:
                raise ValidationError('Вы уже добавили этот рецепт')
        if request.method == 'DELETE':
            if not favorite_exist:
                raise ValidationError('Вы еще не добавили этот рецепт')
        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return UserRecipeSerializer(
            instance,
            context=context).data


class CartRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = "__all__"

    def validate(self, data):
        request = self.context.get('request')
        pk = data.get('recipe')
        obj = get_object_or_404(Recipe, id=pk)
        user = self.context.get('request').user
        carts_exist = User.objects.filter(shopping_cart=user).exists()
        if request.method == 'POST':
            if obj.author == user:
                raise ValidationError('Нельзя добавить свой рецепт')
            if carts_exist:
                raise ValidationError('Вы уже добавили этот рецепт')
        if request.method == 'DELETE':
            if not carts_exist:
                raise ValidationError('Вы еще не добавили этот рецепт')
        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return UserRecipeSerializer(
            instance,
            context=context).data


class UserSubscribtionsSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'recipes', 'recipes_count')

    def validate(self, data):
        request = self.context.get('request')
        if data.get('user') == data.get('subscribers'):
            raise serializers.ValidationError(
                'Нельзя подписываться на самого себя.'
            )
        subscription_exist = User.objects.filter(**data).exists()
        if request.method == 'DELETE':
            if not subscription_exist:
                msg = 'Вы не подписаны на этого пользователя'
                raise serializers.ValidationError(msg)
        if request.method == 'POST':
            if subscription_exist:
                msg = 'Вы уже подписаны на этого пользователя'
                raise serializers.ValidationError(msg)
        return data

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

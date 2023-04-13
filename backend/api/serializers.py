from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.serializers import (
    UserCreateSerializer as DjoserUserCreateSerializer
)
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from recipes.models import (AmountIngredient, Favorite, Ingredient, Recipe,
                            ShoppingCart, Tag)
from users.models import Subscribe

User = get_user_model()


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = '__all__'


class AmountIngredientSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit', 'amount')

    def get_amount(self, obj):
        return obj.ingredient.values('amount')[0]['amount']


class UserSerializer(serializers.ModelSerializer):
    # is_subscribed = serializers.BooleanField(read_only=True)
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'id', 'first_name',
                  'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Subscribe.objects.filter(follower=user, following=obj).exists()


class RecipeSerializer(serializers.ModelSerializer):
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)
    tags = TagSerializer(many=True)
    ingredients = AmountIngredientSerializer(many=True)
    author = UserSerializer(read_only=True)
    image = serializers.SerializerMethodField(
        method_name='get_image_url',
    )

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')
        read_only_fields = (
            'is_favorite',
            'is_shopping_cart',
        )

    def get_image_url(self, obj):
        return obj.image.url


class IngredientsAmountSerializer(serializers.ModelSerializer):
    id = serializers.SlugRelatedField(
        slug_field='id',
        queryset=Ingredient.objects.all()
    )

    class Meta:
        fields = ('id', 'amount')
        model = AmountIngredient


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    ingredients = IngredientsAmountSerializer(
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
            'author'
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

    # @transaction.atomic()
    # def create(self, validated_data):
    #     ingredients = validated_data.pop('ingredients')
    #     tags = validated_data.pop('tags')
    #     image = validated_data.pop('image')
    #     recipe = Recipe.objects.create(image=image, **validated_data)
    #     create_ingredients = [AmountIngredient(
    #         recipe=recipe,
    #         ingredient=ingredient['id'],
    #         amount=ingredient['amount']
    #         )
    #         for ingredient in ingredients
    #     ]
    #     AmountIngredient.objects.bulk_create(
    #         create_ingredients
    #     )
    #     recipe.tags.set(tags)
    #     return recipe

    def add_ingredients(self, instance, ingrs_data):
        for ingredients in ingrs_data:
            ingridient, amount = ingredients.values()
            through = AmountIngredient(
                recipe=instance,
                ingredient=ingridient,
                amount=amount,
            )
            through.save()
        return instance

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        instance = super().create(validated_data)
        return self.add_ingredients(instance, ingredients_data)

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        super().update(instance, validated_data)
        instance.ingredients.clear()
        self.add_ingredients(
            instance, ingredients_data
        )
        instance.tags.set(tags)
        instance.save()
        return instance


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


class AddDeleteMixin(serializers.ModelSerializer):

    def favorite_cart_validator(self, data, model):
        request = self.context.get('request')
        obj = data.get('recipe')
        user = self.context.get('request').user
        if obj.author == user:
            raise ValidationError('Нельзя добавить свой рецепт')
        favorite_exist = model.objects.filter(
            recipe=obj.id,
            user=user).exists()
        if request.method == 'POST':
            if favorite_exist:
                raise ValidationError('Вы уже добавили этот рецепт')
        if request.method == 'DELETE':
            if not favorite_exist:
                raise ValidationError('Вы еще не добавили этот рецепт')
        return data


class FavoriteRecipeSerializer(AddDeleteMixin):

    class Meta:
        model = Favorite
        fields = '__all__'

    def validate(self, data):
        return self.favorite_cart_validator(data, Favorite)


class CartRecipeSerializer(AddDeleteMixin):

    class Meta:
        model = ShoppingCart
        fields = '__all__'

    def validate(self, data):
        return self.favorite_cart_validator(data, ShoppingCart)


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


class SubscribeAddDeleteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subscribe
        fields = '__all__'

    def validate(self, data):
        request = self.context.get('request')
        user = request.user
        pk = data.get('following')
        obj = get_object_or_404(User, id=pk.id)
        if data.get('follower') == data.get('following'):
            raise serializers.ValidationError(
                'Нельзя подписываться на самого себя.'
            )
        subscription_exist = Subscribe.objects.filter(
            follower=user, following=obj).exists()
        if request.method == 'DELETE':
            if not subscription_exist:
                msg = 'Вы не подписаны на этого пользователя'
                raise serializers.ValidationError(msg)
        if request.method == 'POST':
            if subscription_exist:
                msg = 'Вы уже подписаны на этого пользователя'
                raise serializers.ValidationError(msg)
        return data
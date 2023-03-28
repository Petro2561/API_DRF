from django.contrib.auth import get_user_model
from django.db.models import Exists, F, OuterRef, Sum, Value
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import SetPasswordSerializer
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import filters, viewsets
from rest_framework.decorators import action
# from rest_framework.permissions import IsAuthenticated
from .permissions import (AdminOrReadOnly, AuthorStaffOrReadOnly,
                             DjangoModelPermissions, IsAuthenticated)
from rest_framework.response import Response
from rest_framework.status import (HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT,
                                   HTTP_400_BAD_REQUEST)

from .filters import IngredientFilter, RecipeFilter
from recipes.models import (AmountIngredient, Favorite, Ingredient, Recipe,
                            ShoppingCart, Tag)
from users.models import Subscribe

from .paginators import PageLimitPagination
from .serializers import (CartRecipeSerializer, FavoriteRecipeSerializer,
                          IngredientSerializer, RecipeSerializer,
                          RecipeCreateUpdateSerializer,
                          SubscribeAddDeleteSerializer, TagSerializer,
                          UserCreateSerializer, UserRecipeSerializer,
                          UserSerializer, UserSubscribtionsSerializer)

User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = PageLimitPagination
    http_method_names = ['get', 'post', 'delete']
    permission_classes = (DjangoModelPermissions,)

    def get_queryset(self):
        user = self.request.user.id
        is_subscribed = Subscribe.objects.filter(
            following=OuterRef('pk'),
            follower=user
        )
        return (User.objects.annotate(is_subscribed=Exists(is_subscribed))
                if self.request.user.is_authenticated
                else User.objects.annotate(
                is_subscribed=Value(False)))

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action == 'set_password':
            return SetPasswordSerializer
        if self.action == 'subscriptions':
            return UserSubscribtionsSerializer
        if self.action == 'subscribe':
            return SubscribeAddDeleteSerializer
        return UserSerializer

    @action(detail=False)
    def me(self, request):
        user = self.request.user
        me = User.objects.filter(id=user.id)
        context = {'request': request}
        serializer = UserSerializer(me, many=True, context=context)
        return Response(serializer.data)

    @action(methods=['post'], detail=False,
            permission_classes=[IsAuthenticated])
    def set_password(self, request, *args, **kwargs):
        return DjoserUserViewSet.set_password(self, request, *args, **kwargs)

    @action(detail=False)
    def subscriptions(self, request):
        user = self.request.user
        subscribes = User.objects.filter(subscribing__follower=user)
        page = self.paginate_queryset(subscribes)
        context = {'request': request}
        if page is not None:
            serializer = self.get_serializer(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(subscribes,
                                         many=True, context=context)
        return Response(serializer.data)

    @action(methods=['post'],
            detail=True,
            permission_classes=(IsAuthenticated,)
            )
    def subscribe(self, request, id=None):
        user = self.request.user
        context = {'request': request}
        data = {
            'follower': user.id,
            'following': id,
        }
        serializer = self.get_serializer(data=data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        queryset = self.get_queryset().get(id=id)
        instance_serializer = UserSubscribtionsSerializer(
            queryset, context=context)
        return Response(instance_serializer.data, HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id=None):
        user = self.request.user
        obj = get_object_or_404(User, id=id)
        context = {'request': request}
        data = {
            'follower': user.id,
            'following': id,
        }
        serializer = SubscribeAddDeleteSerializer(data=data, context=context)
        serializer.is_valid(raise_exception=True)
        instance = Subscribe.objects.filter(follower=user, following=obj)
        instance.delete()
        return Response(HTTP_204_NO_CONTENT)


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    permission_classes = (AdminOrReadOnly,)
    http_method_names = ['get']


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AdminOrReadOnly,)
    http_method_names = ['get']


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = PageLimitPagination
    http_method_names = ['get', 'post', 'delete', 'patch']
    permission_classes = (AuthorStaffOrReadOnly,)

    def get_queryset(self):
        user = self.request.user.id
        is_favorite = Favorite.objects.filter(
            user=user,
            recipe=OuterRef('pk'),
        )
        is_in_shopping_cart = ShoppingCart.objects.filter(
            recipe=OuterRef('pk'),
            user=user
        )
        return Recipe.objects.annotate(
            is_favorited=Exists(is_favorite),
            is_in_shopping_cart=Exists(is_in_shopping_cart)
        )

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeCreateUpdateSerializer
        if self.action == 'favorite':
            return FavoriteRecipeSerializer
        if self.action == 'shopping_cart':
            return CartRecipeSerializer
        return RecipeSerializer

    def create_update_repr(self, instanse, status):
        instance_serializer = RecipeSerializer(
            instanse, context={'request': self.request})
        return Response(instance_serializer.data, status)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_recipe = serializer.save(author=self.request.user)

        return self.create_update_repr(new_recipe, HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return self.create_update_repr(instance, HTTP_200_OK)

    def cart_favorite_add_delete(self, request, model, pk):
        user = self.request.user
        obj = get_object_or_404(Recipe, id=pk)
        serializer = self.get_serializer(
            data={'recipe': pk, 'user': user.id},
            context={'request': request},
        )
        instance = model.objects.filter(recipe=pk, user=user)
        serializer.is_valid(raise_exception=True)
        if request.method == 'DELETE':
            instance.delete()
            return Response(HTTP_204_NO_CONTENT)

        model.objects.get_or_create(recipe=obj, user=user)
        serializer = UserRecipeSerializer(obj)
        return Response(serializer.data, status=HTTP_201_CREATED)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        return self.cart_favorite_add_delete(request, Favorite, pk)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self.cart_favorite_add_delete(request, ShoppingCart, pk)

    @action(methods=['get'], detail=False,
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = self.request.user
        if not user.shoppingcart_set.exists():
            return Response(status=HTTP_400_BAD_REQUEST)
        ingredients = AmountIngredient.objects.filter(
            recipe__cart__user=user
        ).values(
            ingridient=F('ingredient__name'),
            measure=F('ingredient__measurument_unit'),
        ).annotate(amount=Sum('amount'))

        filename = f'{user.username}_shopping_cart.txt'
        shopping_list = (
            f'Список покупок для: {user.first_name}\n\n'
        )
        for ing in ingredients:
            shopping_list += (
                f'{ing["ingridient"].capitalize()}'
                f'({ing["measure"]}): - {ing["amount"]} \n'
            )

        response = HttpResponse(
            shopping_list, content_type='text.txt; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response

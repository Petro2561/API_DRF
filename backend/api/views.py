from django.contrib.auth import get_user_model
from django.db.models import Exists, F, OuterRef, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import SetPasswordSerializer
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (HTTP_201_CREATED, HTTP_204_NO_CONTENT,
                                   HTTP_400_BAD_REQUEST)

from api.filters import RecipeFilter
from recipes.models import AmountIngredient, Ingredient, Recipe, Tag

from .paginators import RecipePagination
from .permissions import AuthorOrReadOnly
from .serializers import (FavoriteRecipeSerializer, IngredientSerializer,
                          RecipeSerializer, TagSerializer,
                          UserCreateSerializer, UserRecipeSerializer,
                          UserSerializer, UserSubscribtionsSerializer)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = RecipePagination
    http_method_names = ['get', 'post', 'delete']
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        is_subscribed = User.objects.filter(
            subscribed=OuterRef('pk'),
            username=user
        )
        return User.objects.annotate(is_subscribed=Exists(is_subscribed))


    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'set_password':
            return SetPasswordSerializer
        elif self.action == 'subscriptions':
            return UserSubscribtionsSerializer
        elif self.action == 'subscribe':
            return UserSubscribtionsSerializer
        return UserSerializer

    @action(detail=False)
    def me(self, request):
        user = self.request.user
        me = User.objects.filter(id=user.id)
        serializer = UserSerializer(me, many=True, context={'request': request})
        return Response(serializer.data)

    @action(methods=['post'], detail=False)
    def set_password(self, request, *args, **kwargs):
        return DjoserUserViewSet.set_password(self, request, *args, **kwargs)

    @action(detail=False)
    def subscriptions(self, request):
        user = self.request.user
        subscribes = User.objects.filter(subscribers=user)
        page = self.paginate_queryset(subscribes)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(subscribes, many=True, context={'request': request})
        return Response(serializer.data)

    @action(methods=['post'], detail=True)
    def subscribe(self, request, pk=None):
        user = self.request.user
        context = {'request': request}
        obj = get_object_or_404(User, id=pk)
        data = {
            'user': user,
            'subscribers': obj.subscribers,
        }
        serializer = self.get_serializer(data=data, context=context)
        serializer.is_valid(raise_exception=True)
        user.subscribed.add(obj)
        queryset = self.get_queryset().get(id=pk)
        instance_serializer = UserSubscribtionsSerializer(queryset, context=context)
        return Response(instance_serializer.data, HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, pk=None):
        user = self.request.user
        obj = get_object_or_404(User, id=pk)
        user.subscribed.remove(obj)
        return Response(HTTP_204_NO_CONTENT)


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    http_method_names = ['get']


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    http_method_names = ['get']


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = RecipePagination
    http_method_names = ['get', 'post', 'delete', 'patch']
    permission_classes = (AuthorOrReadOnly,)

    def get_serializer_class(self):
        if self.action == 'favorite':
            return UserRecipeSerializer
        return RecipeSerializer


    @action(detail=True, methods=['post'])
    def favorite(self, request, pk=None):
        user = self.request.user
        obj = get_object_or_404(Recipe, id=pk)
        serializer = FavoriteRecipeSerializer(
            data={'pk': pk},
            context={'request': request.data},
        )
        serializer.is_valid(raise_exception=True)
        user.favorites.add(obj)
        return Response(serializer.data, status=HTTP_201_CREATED)


    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        user = self.request.user
        obj = get_object_or_404(Recipe, id=pk)
        user.favorites.remove(obj)
        return Response(HTTP_204_NO_CONTENT)

    def get_queryset(self):
        user = self.request.user
        is_favorite = User.objects.filter(
            favorites=OuterRef('pk'),
            username=user
        )
        is_in_shopping_cart = User.objects.filter(
            carts=OuterRef('pk'),
            username=user
        )
        return Recipe.objects.annotate(
            is_favorited=Exists(is_favorite),
            is_in_shopping_cart=Exists(is_in_shopping_cart)
        )

    @action(methods=['post'], detail=True)
    def shopping_cart(self, request, pk=None):
        user = self.request.user
        context = {'request': request}
        obj = get_object_or_404(Recipe, id=pk)
        serializer = UserRecipeSerializer(data={'recipe': pk}, context=context)
        user.carts.add(obj)
        return Response(serializer.data, status=HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        user = self.request.user
        obj = get_object_or_404(Recipe, id=pk)
        user.carts.remove(obj)
        return Response(HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False)
    def download_shopping_cart(self, request):
        user = self.request.user
        if not user.carts.exists():
            return Response(status=HTTP_400_BAD_REQUEST)
        ingredients = AmountIngredient.objects.filter(
            recipe__shopping_cart=user
        ).values(
            ingridient=F('recipe__name'),
            measure=F('ingredient__measurument_unit'),
        ).annotate(amount=Sum('amount'))

        filename = f'{user.username}_shopping_cart.txt'
        shopping_list = (
            f'Список покупок для:\n\n{user.first_name}\n\n'
        )
        for ing in ingredients:
            shopping_list += (
                f'{ing["ingridient"]}: {ing["amount"]} {ing["measure"]}\n'
            )
        response = HttpResponse(
            shopping_list, content_type='text.txt; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from recipes.models import Ingredient, Tag, Recipe
from .serializers import IngredientSerializer, TagSerializer, RecipeSerializer, UserSerializer
from rest_framework import filters, mixins
from django_filters.rest_framework import DjangoFilterBackend
from api.filters import RecipeFilter
from .paginators import RecipePagination
from users.models import CustomUser

from django.contrib.auth import get_user_model

from django.shortcuts import get_object_or_404

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = RecipePagination

    @action(detail=False)
    def me(self, request):
        user = self.request.user
        me = User.objects.filter(id=user.id)
        serializer = UserSerializer(me, many=True, context={'request': request})
        return Response(serializer.data)


class IngredientViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)


class TagViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                 viewsets.GenericViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = RecipePagination

    # @action(detail=True, methods=['post', 'delete'])
    # def favorite(self, request, id=None):
    #     """ Принимаем запрос на еднопинт recipe/id/favorite

    #     добавляет связь
    #     """
    #     user = request.user
    #     author = get_object_or_404(User, pk=id)
    #     if self.request.method == 'POST':
    #         if user == author:
    #             message = {'Нельзя подписаться на самого себя'}
    #             return Response(message, status=status.HTTP_400_BAD_REQUEST)


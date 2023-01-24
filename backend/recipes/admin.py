from django.contrib import admin

from .models import AmountIngredient, Ingredient, Recipe, Tag


class IngredientInRecipeAdmin(admin.TabularInline):
    model = AmountIngredient


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'favorite_count')
    list_filter = ('name', 'author', 'tags')
    search_fields = ('name',)

    inlines = [
        IngredientInRecipeAdmin,
    ]

    def favorite_count(self, obj):
        return obj.favorite.count()

    favorite_count.short_description = 'В избранном'


class IngredientAdmin(admin.ModelAdmin):
    search_fields = ('name',)


admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(AmountIngredient)
admin.site.register(Tag)

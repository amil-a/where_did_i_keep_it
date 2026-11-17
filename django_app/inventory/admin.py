from django.contrib import admin

from .models import Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "location", "date_added")
    list_filter = ("category",)
    search_fields = ("name", "description", "location")

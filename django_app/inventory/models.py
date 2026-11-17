from django.db import models
from django.urls import reverse


class Item(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(
        help_text="Describe the item: colour, size, what it is used for."
    )
    category = models.CharField(max_length=100)
    location = models.CharField(
        max_length=300,
        help_text="Example: House → Bedroom → Wardrobe → Second Drawer → Blue Box",
    )
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_added"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("item_detail", args=[self.pk])

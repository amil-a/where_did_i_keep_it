from django import forms

from .models import Item


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ["name", "description", "category", "location"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "HDMI Cable"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Black cable used to connect laptop to monitor",
                }
            ),
            "category": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Cables", "list": "category-options"}
            ),
            "location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "House → Bedroom → Wardrobe → Second Drawer → Blue Box",
                }
            ),
        }

    def _clean_text(self, field):
        value = self.cleaned_data[field].strip()
        if not value:
            raise forms.ValidationError("This field cannot be blank.")
        return value

    def clean_name(self):
        return self._clean_text("name")

    def clean_description(self):
        value = self._clean_text("description")
        if len(value) < 10:
            raise forms.ValidationError(
                "Please write at least 10 characters. Search works better with a real description."
            )
        return value

    def clean_category(self):
        return self._clean_text("category")

    def clean_location(self):
        return self._clean_text("location")


class SearchForm(forms.Form):
    query = forms.CharField(
        max_length=300,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "e.g. that black cable for connecting my laptop to the monitor",
                "autofocus": True,
            }
        ),
    )

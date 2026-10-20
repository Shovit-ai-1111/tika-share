from django import forms

from .models import Card


class CardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = ["name", "photo", "qr_image"]
        labels = {"name": "Your name", "photo": "Your photo", "qr_image": "Your QR screenshot"}
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Sita", "autocomplete": "given-name"}),
            "photo": forms.FileInput(attrs={"accept": "image/*", "data-preview": "photo-preview"}),
            "qr_image": forms.FileInput(attrs={"accept": "image/*", "data-preview": "qr-preview"}),
        }

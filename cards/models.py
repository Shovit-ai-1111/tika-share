import uuid

from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils.crypto import get_random_string

from .images import process_photo, process_qr, validate_upload_size

# No look-alike characters (0/o, 1/l/i) so links are easy to read out or type.
SLUG_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def new_slug():
    return get_random_string(8, SLUG_ALPHABET)


# Uploads are re-encoded on save (see Card.save), so the stored name/extension is ours, not the user's.
def photo_path(instance, filename):
    return f"photos/{uuid.uuid4().hex}.jpg"


def qr_path(instance, filename):
    return f"qr/{uuid.uuid4().hex}.png"


class Card(models.Model):
    """One shareable face + the QR that appears after the friend adds tika and jamara."""

    slug = models.SlugField(max_length=16, unique=True, editable=False, default=new_slug)
    name = models.CharField(max_length=60, help_text="Shown to your friend, e.g. “Sita”.")
    photo = models.ImageField(
        upload_to=photo_path,
        validators=[validate_upload_size],
        help_text="A clear, front-facing photo works best.",
    )
    qr_image = models.ImageField(
        "QR screenshot",
        upload_to=qr_path,
        validators=[validate_upload_size],
        help_text="Screenshot of your eSewa / Fonepay / bank QR.",
    )
    is_featured = models.BooleanField(default=False, help_text="Show this card on the home page.")
    is_active = models.BooleanField(
        default=True, help_text="Untick to hide the card. Its share link will stop working."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def get_absolute_url(self):
        return reverse("card", args=[self.slug])

    def save(self, *args, **kwargs):
        if self._state.adding:
            while Card.objects.filter(slug=self.slug).exists():
                self.slug = new_slug()
            old = None
        else:
            old = Card.objects.filter(pk=self.pk).first()

        # Re-encode freshly uploaded images (from the public form and from the admin alike).
        for field_name, process in (("photo", process_photo), ("qr_image", process_qr)):
            file = getattr(self, field_name)
            if file and not file._committed:
                file.save("upload", ContentFile(process(file)), save=False)

        super().save(*args, **kwargs)

        # If an image was replaced, remove the old file from disk.
        if old:
            for field_name in ("photo", "qr_image"):
                old_file = getattr(old, field_name)
                if old_file and old_file.name != getattr(self, field_name).name:
                    old_file.delete(save=False)


@receiver(post_delete, sender=Card)
def delete_card_files(sender, instance, **kwargs):
    for file in (instance.photo, instance.qr_image):
        if file:
            file.delete(save=False)

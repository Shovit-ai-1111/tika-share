from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Card


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("thumb", "name", "slug", "is_featured", "is_active", "created_at", "open_link")
    list_display_links = ("thumb", "name")
    list_editable = ("is_featured", "is_active")
    list_filter = ("is_featured", "is_active", "created_at")
    search_fields = ("name", "slug")
    date_hierarchy = "created_at"
    readonly_fields = ("slug", "created_at", "photo_preview", "qr_preview", "share_path")
    fields = (
        "name",
        "photo",
        "photo_preview",
        "qr_image",
        "qr_preview",
        "is_featured",
        "is_active",
        "share_path",
        "slug",
        "created_at",
    )

    @admin.display(description="Photo")
    def thumb(self, obj):
        if not obj.photo:
            return "-"
        return format_html(
            '<img src="{}" alt="" style="height:56px;width:56px;object-fit:cover;border-radius:50%">',
            obj.photo.url,
        )

    @admin.display(description="Photo preview")
    def photo_preview(self, obj):
        if not obj.photo:
            return "-"
        return format_html('<img src="{}" alt="" style="max-height:200px;border-radius:8px">', obj.photo.url)

    @admin.display(description="QR preview")
    def qr_preview(self, obj):
        if not obj.qr_image:
            return "-"
        return format_html('<img src="{}" alt="" style="max-height:200px">', obj.qr_image.url)

    @admin.display(description="Share link")
    def share_path(self, obj):
        if obj._state.adding:
            return "Available after saving."
        url = reverse("card", args=[obj.slug])
        return format_html('<a href="{0}" target="_blank" rel="noopener">{0}</a>', url)

    @admin.display(description="Open")
    def open_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Open</a>', reverse("card", args=[obj.slug])
        )

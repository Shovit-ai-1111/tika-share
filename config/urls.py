from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve


def serve_media(request, path):
    """Serve uploaded images. Fine for a small app; put nginx/S3 in front for heavy traffic."""
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns = [
    path("admin/", admin.site.urls),
    re_path(r"^media/(?P<path>.*)$", serve_media),
    path("", include("cards.urls")),
]

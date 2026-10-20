from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import CardForm
from .models import Card

# Slugs of the cards created in this browser session. This is what lets a creator reopen the
# share page and delete their card without needing an account.
SESSION_KEY = "my_cards"


def _absolute(request, path):
    base = settings.PUBLIC_BASE_URL or f"{request.scheme}://{request.get_host()}"
    return base + path


def _owns(request, slug):
    return slug in request.session.get(SESSION_KEY, [])


def home(request):
    featured = Card.objects.filter(is_active=True, is_featured=True)[:12]
    return render(request, "cards/home.html", {"featured": featured})


def create(request):
    if request.method == "POST":
        form = CardForm(request.POST, request.FILES)
        if form.is_valid():
            card = form.save()
            request.session[SESSION_KEY] = [*request.session.get(SESSION_KEY, []), card.slug]
            return redirect("share", slug=card.slug)
    else:
        form = CardForm()
    return render(request, "cards/create.html", {"form": form})


def share(request, slug):
    card = get_object_or_404(Card, slug=slug, is_active=True)
    if not _owns(request, slug):
        return redirect("card", slug=slug)

    link = _absolute(request, reverse("card", args=[slug]))
    text = f"{card.name} would love your Dashain tika & jamara! Put it on their face 🙏"
    context = {
        "card": card,
        "link": link,
        "share_text": text,
        "whatsapp_url": "https://wa.me/?text=" + quote(f"{text} {link}"),
        "viber_url": "viber://forward?text=" + quote(f"{text} {link}"),
        "facebook_url": "https://www.facebook.com/sharer/sharer.php?u=" + quote(link, safe=""),
    }
    return render(request, "cards/share.html", context)


def card(request, slug):
    """The page the friend opens: drag tika + jamara onto the face, press Done, QR appears."""
    card = get_object_or_404(Card, slug=slug, is_active=True)
    context = {
        "card": card,
        "page_url": _absolute(request, reverse("card", args=[slug])),
        # Absolute URL so WhatsApp / Viber / Facebook link previews show the face.
        "og_image": _absolute(request, card.photo.url),
    }
    return render(request, "cards/card.html", context)


def my_cards(request):
    slugs = request.session.get(SESSION_KEY, [])
    cards = Card.objects.filter(slug__in=slugs, is_active=True)
    return render(request, "cards/my_cards.html", {"cards": cards})


@require_POST
def delete(request, slug):
    card = get_object_or_404(Card, slug=slug)
    if not _owns(request, slug):
        return redirect("card", slug=slug)
    card.delete()
    request.session[SESSION_KEY] = [s for s in request.session.get(SESSION_KEY, []) if s != slug]
    messages.success(request, "Your card was deleted.")
    return redirect("my_cards")

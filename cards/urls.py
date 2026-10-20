from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("create/", views.create, name="create"),
    path("my/", views.my_cards, name="my_cards"),
    path("c/<slug:slug>/", views.card, name="card"),
    path("c/<slug:slug>/share/", views.share, name="share"),
    path("c/<slug:slug>/delete/", views.delete, name="delete"),
]

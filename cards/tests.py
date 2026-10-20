import shutil
import tempfile
from io import BytesIO, StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Card

TEMP_MEDIA = tempfile.mkdtemp(prefix="tika-test-media-")


def make_image(fmt="PNG", size=(40, 60), color=(200, 30, 60), name="pic", exif=False):
    buf = BytesIO()
    img = Image.new("RGB", size, color)
    kwargs = {}
    if exif:
        # EXIF with a GPS IFD pointer: the stored copy must not keep it.
        data = Image.Exif()
        data[0x0112] = 6  # orientation: rotate 270 to display
        data[0x8825] = {1: "N"}  # GPSInfo
        kwargs["exif"] = data
    img.save(buf, fmt, **kwargs)
    ext = {"PNG": "png", "JPEG": "jpg"}[fmt]
    ctype = {"PNG": "image/png", "JPEG": "image/jpeg"}[fmt]
    return SimpleUploadedFile(f"{name}.{ext}", buf.getvalue(), content_type=ctype)


@override_settings(MEDIA_ROOT=TEMP_MEDIA, PUBLIC_BASE_URL="")
class CardTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def create_via_form(self, **overrides):
        data = {
            "name": "Sita",
            "photo": make_image("JPEG", name="face"),
            "qr_image": make_image("PNG", size=(300, 600), name="qr"),
        }
        data.update(overrides)
        return self.client.post(reverse("create"), data)

    # ---- public pages -------------------------------------------------

    def test_home_and_create_pages_render(self):
        self.assertContains(self.client.get(reverse("home")), "Create your own")
        self.assertContains(self.client.get(reverse("create")), "Create my link")

    def test_home_lists_only_featured_active_cards(self):
        self.create_via_form(name="Hidden")
        self.create_via_form(name="Shown")
        Card.objects.filter(name="Shown").update(is_featured=True)
        Card.objects.filter(name="Hidden").update(is_featured=False)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Try one")
        self.assertContains(response, "Shown")
        self.assertNotContains(response, "Hidden")

    def test_create_redirects_to_share_and_stores_card(self):
        response = self.create_via_form()
        card = Card.objects.get()
        self.assertRedirects(response, reverse("share", args=[card.slug]))
        self.assertEqual(card.name, "Sita")
        self.assertEqual(len(card.slug), 8)

    def test_share_page_shows_absolute_link(self):
        self.create_via_form()
        card = Card.objects.get()
        response = self.client.get(reverse("share", args=[card.slug]))
        self.assertContains(response, f"http://testserver/c/{card.slug}/")
        self.assertContains(response, "wa.me")

    def test_public_base_url_is_used_for_share_links(self):
        self.create_via_form()
        card = Card.objects.get()
        with self.settings(PUBLIC_BASE_URL="https://tika.example.com"):
            response = self.client.get(reverse("share", args=[card.slug]))
        self.assertContains(response, f"https://tika.example.com/c/{card.slug}/")

    def test_friend_page_has_face_tray_done_and_qr(self):
        self.create_via_form()
        card = Card.objects.get()
        friend = self.client_class()  # a different browser, no session
        response = friend.get(reverse("card", args=[card.slug]))
        self.assertContains(response, 'id="face"')
        self.assertContains(response, 'data-tray="tika"')
        self.assertContains(response, 'data-tray="jamara"')
        self.assertContains(response, 'id="done-btn"')
        self.assertContains(response, card.qr_image.url)
        self.assertContains(response, 'property="og:image" content="http://testserver')

    # ---- ownership ----------------------------------------------------

    def test_share_page_is_only_for_the_creator(self):
        self.create_via_form()
        card = Card.objects.get()
        stranger = self.client_class()
        response = stranger.get(reverse("share", args=[card.slug]))
        self.assertRedirects(response, reverse("card", args=[card.slug]))

    def test_my_cards_lists_only_this_browsers_cards(self):
        self.create_via_form(name="Mine")
        other = self.client_class()
        other.post(
            reverse("create"),
            {"name": "Theirs", "photo": make_image("JPEG"), "qr_image": make_image("PNG")},
        )
        response = self.client.get(reverse("my_cards"))
        self.assertContains(response, "Mine")
        self.assertNotContains(response, "Theirs")

    def test_owner_can_delete_and_files_are_removed(self):
        self.create_via_form()
        card = Card.objects.get()
        photo_file, qr_file = Path(card.photo.path), Path(card.qr_image.path)
        self.assertTrue(photo_file.exists() and qr_file.exists())

        response = self.client.post(reverse("delete", args=[card.slug]))
        self.assertRedirects(response, reverse("my_cards"))
        self.assertFalse(Card.objects.exists())
        self.assertFalse(photo_file.exists())
        self.assertFalse(qr_file.exists())

    def test_stranger_cannot_delete(self):
        self.create_via_form()
        card = Card.objects.get()
        stranger = self.client_class()
        stranger.post(reverse("delete", args=[card.slug]))
        self.assertTrue(Card.objects.filter(pk=card.pk).exists())

    def test_delete_requires_post(self):
        self.create_via_form()
        card = Card.objects.get()
        self.assertEqual(self.client.get(reverse("delete", args=[card.slug])).status_code, 405)

    def test_inactive_card_is_404_everywhere(self):
        self.create_via_form()
        card = Card.objects.get()
        Card.objects.filter(pk=card.pk).update(is_active=False)
        self.assertEqual(self.client.get(reverse("card", args=[card.slug])).status_code, 404)
        self.assertEqual(self.client.get(reverse("share", args=[card.slug])).status_code, 404)

    def test_unknown_slug_is_404(self):
        self.assertEqual(self.client.get(reverse("card", args=["nope1234"])).status_code, 404)

    # ---- upload validation & image processing ------------------------

    def test_non_image_upload_is_rejected(self):
        fake = SimpleUploadedFile("evil.png", b"<script>alert(1)</script>", content_type="image/png")
        response = self.create_via_form(photo=fake)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Card.objects.exists())
        self.assertContains(response, "valid image")

    def test_svg_upload_is_rejected(self):
        svg = SimpleUploadedFile(
            "x.svg", b'<svg xmlns="http://www.w3.org/2000/svg"><script>1</script></svg>',
            content_type="image/svg+xml",
        )
        response = self.create_via_form(qr_image=svg)
        self.assertFalse(Card.objects.exists())
        self.assertEqual(response.status_code, 200)

    def test_missing_fields_are_rejected(self):
        response = self.client.post(reverse("create"), {"name": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Card.objects.exists())

    def test_oversized_upload_is_rejected(self):
        # A genuinely valid PNG, padded past the limit (trailing bytes after IEND are ignored by Pillow),
        # so the size check is what rejects it rather than the "is this an image" check.
        buf = BytesIO()
        Image.new("RGB", (10, 10), (1, 2, 3)).save(buf, "PNG")
        big = SimpleUploadedFile(
            "big.png", buf.getvalue() + b"0" * (8 * 1024 * 1024), content_type="image/png"
        )
        response = self.create_via_form(photo=big)
        self.assertFalse(Card.objects.exists())
        self.assertContains(response, "too large")

    def test_photo_is_reencoded_as_jpeg_without_gps_and_rotated(self):
        photo = make_image("JPEG", size=(40, 60), exif=True)  # stored sideways, orientation=6
        self.create_via_form(photo=photo)
        card = Card.objects.get()
        self.assertTrue(card.photo.name.endswith(".jpg"))
        self.assertNotIn("face", card.photo.name)  # user's filename is not kept
        with Image.open(card.photo.path) as stored:
            self.assertEqual(stored.format, "JPEG")
            self.assertNotIn(0x8825, stored.getexif())  # GPS gone
            self.assertEqual(stored.size, (60, 40))  # orientation applied -> now landscape

    def test_large_photo_is_downscaled_and_qr_stays_png(self):
        self.create_via_form(
            photo=make_image("PNG", size=(3200, 2400)),
            qr_image=make_image("JPEG", size=(1080, 2400)),
        )
        card = Card.objects.get()
        with Image.open(card.photo.path) as photo:
            self.assertLessEqual(max(photo.size), 1600)
            self.assertEqual(photo.format, "JPEG")
        with Image.open(card.qr_image.path) as qr:
            self.assertEqual(qr.format, "PNG")
            self.assertEqual(qr.size, (1080, 2400))  # under the 2400px cap: untouched

    def test_transparent_png_photo_is_flattened_on_white(self):
        buf = BytesIO()
        Image.new("RGBA", (20, 20), (0, 0, 0, 0)).save(buf, "PNG")
        upload = SimpleUploadedFile("t.png", buf.getvalue(), content_type="image/png")
        self.create_via_form(photo=upload)
        card = Card.objects.get()
        with Image.open(card.photo.path) as stored:
            r, g, b = stored.convert("RGB").getpixel((5, 5))
            self.assertGreater(min(r, g, b), 240)

    def test_replacing_an_image_removes_the_old_file(self):
        self.create_via_form()
        card = Card.objects.get()
        old = Path(card.photo.path)
        card.photo = make_image("JPEG", name="new")
        card.save()
        card.refresh_from_db()
        self.assertFalse(old.exists())
        self.assertTrue(Path(card.photo.path).exists())

    def test_saving_without_changing_images_keeps_files(self):
        self.create_via_form()
        card = Card.objects.get()
        photo_path = Path(card.photo.path)
        card.name = "Sita K"
        card.save()
        self.assertTrue(photo_path.exists())


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AdminTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("boss", "b@example.com", "pw-12345-xyz")
        self.client.force_login(self.admin)

    def test_admin_can_add_featured_card_and_it_is_processed(self):
        response = self.client.post(
            reverse("admin:cards_card_add"),
            {
                "name": "Demo",
                "photo": make_image("PNG", size=(2000, 2000)),
                "qr_image": make_image("PNG", size=(300, 300)),
                "is_featured": "on",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["adminform"].form.errors)
        card = Card.objects.get(name="Demo")
        self.assertTrue(card.is_featured)
        with Image.open(card.photo.path) as photo:
            self.assertEqual(photo.format, "JPEG")
            self.assertLessEqual(max(photo.size), 1600)
        self.assertContains(self.client.get(reverse("home")), "Demo")

    def test_admin_list_and_change_pages_render(self):
        card = Card(name="Demo")
        card.photo = make_image("JPEG")
        card.qr_image = make_image("PNG")
        card.save()
        self.assertContains(self.client.get(reverse("admin:cards_card_changelist")), "Demo")
        self.assertContains(self.client.get(reverse("admin:cards_card_change", args=[card.pk])), card.slug)


class EnsureAdminCommandTests(TestCase):
    def run_command(self, **env):
        import os
        from unittest import mock

        out = StringIO()
        with mock.patch.dict(os.environ, env, clear=False):
            call_command("ensure_admin", stdout=out)
        return out.getvalue()

    def test_creates_admin_once_and_never_overwrites(self):
        self.run_command(ADMIN_USERNAME="root1", ADMIN_PASSWORD="first-pass-123", ADMIN_EMAIL="r@example.com")
        user = get_user_model().objects.get(username="root1")
        self.assertTrue(user.is_superuser and user.check_password("first-pass-123"))

        output = self.run_command(ADMIN_USERNAME="root1", ADMIN_PASSWORD="changed-pass-456")
        self.assertIn("already exists", output)
        user.refresh_from_db()
        self.assertTrue(user.check_password("first-pass-123"))

    def test_skips_when_no_password(self):
        import os
        from unittest import mock

        env = {k: v for k, v in os.environ.items() if k != "ADMIN_PASSWORD"}
        with mock.patch.dict(os.environ, env, clear=True):
            out = StringIO()
            call_command("ensure_admin", stdout=out)
        self.assertIn("skipping", out.getvalue())
        self.assertFalse(get_user_model().objects.exists())

    def test_refuses_default_password_outside_debug(self):
        with self.settings(DEBUG=False), self.assertRaises(CommandError):
            self.run_command(ADMIN_USERNAME="x", ADMIN_PASSWORD="admin12345")
        self.assertFalse(get_user_model().objects.exists())

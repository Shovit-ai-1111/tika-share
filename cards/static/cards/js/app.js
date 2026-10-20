/* Small helpers used across pages: image previews, copy link, native share, confirm. */
(() => {
  'use strict';

  const MAX_MB = 8; // keep in sync with MAX_UPLOAD_MB in cards/images.py

  // --- Preview the chosen image on the create form, and warn early about huge files ---
  document.querySelectorAll('input[type="file"][data-preview]').forEach((input) => {
    const preview = document.getElementById(input.dataset.preview);
    if (!preview) return;

    const note = document.createElement('p');
    note.className = 'error';
    note.setAttribute('role', 'alert');
    note.hidden = true;
    input.insertAdjacentElement('afterend', note);

    let objectUrl = null;
    const reset = () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = null;
      preview.hidden = true;
      preview.removeAttribute('src');
      note.hidden = true;
    };

    input.addEventListener('change', () => {
      reset();
      const file = input.files && input.files[0];
      if (!file) return;
      if (file.size > MAX_MB * 1024 * 1024) {
        note.textContent = `That image is too large. Please choose one under ${MAX_MB} MB.`;
        note.hidden = false;
        input.value = '';
        return;
      }
      objectUrl = URL.createObjectURL(file);
      preview.src = objectUrl;
      preview.hidden = false;
    });
  });

  // --- Copy the share link ---
  document.querySelectorAll('[data-copy-from]').forEach((button) => {
    const input = document.getElementById(button.dataset.copyFrom);
    const status = document.getElementById('copied');
    if (!input) return;

    input.addEventListener('focus', () => input.select());

    button.addEventListener('click', async () => {
      let ok = false;
      try {
        await navigator.clipboard.writeText(input.value);
        ok = true;
      } catch (_) {
        // Clipboard API needs HTTPS (or localhost); fall back to the old way.
        input.select();
        input.setSelectionRange(0, input.value.length);
        try { ok = document.execCommand('copy'); } catch (__) { ok = false; }
      }
      if (status) {
        status.textContent = ok ? 'Link copied!' : 'Press Ctrl/Cmd + C to copy the link.';
        status.hidden = false;
      }
    });
  });

  // --- Native share sheet (phones) ---
  if (navigator.share) {
    document.querySelectorAll('[data-native-share]').forEach((button) => {
      button.hidden = false;
      button.addEventListener('click', () => {
        navigator
          .share({ title: button.dataset.title, text: button.dataset.text, url: button.dataset.url })
          .catch(() => {}); // user dismissed the sheet
      });
    });
  }

  // --- Confirm before destructive actions ---
  document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
})();

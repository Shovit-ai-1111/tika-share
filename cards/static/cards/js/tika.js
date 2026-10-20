/* The friend's page: drag the tika and jamara onto the face, press Done, the QR pops up.
 *
 * Uses Pointer Events (not HTML5 drag-and-drop) so the same code works with a mouse, a finger
 * or a pen. Tapping/pressing Enter on a tray item also places it, and placed items can be
 * moved with the arrow keys, so it is usable without dragging.
 */
(() => {
  'use strict';

  const face = document.getElementById('face');
  if (!face) return;

  const doneBtn = document.getElementById('done-btn');
  const sizeUp = document.getElementById('size-up');
  const sizeDown = document.getElementById('size-down');
  const startOver = document.getElementById('start-over');
  const hint = document.getElementById('hint');
  const dialog = document.getElementById('qr-dialog');

  const SRC = { tika: face.dataset.tikaSrc, jamara: face.dataset.jamaraSrc };
  // Where each item lands when tapped (x/y = centre, in % of the photo) and its width in % of the photo.
  const DEFAULTS = {
    tika: { x: 50, y: 26, w: 13, label: 'Tika' },
    jamara: { x: 50, y: 10, w: 34, label: 'Jamara' },
  };
  const DRAG_THRESHOLD = 6; // px of movement before a press on the tray counts as a drag
  const SIZE_STEP = 1.12;

  const placed = {}; // name -> { el, x, y, w }
  let selected = null;

  const clamp = (n, lo, hi) => Math.min(hi, Math.max(lo, n));
  const toPercent = (clientX, clientY) => {
    const r = face.getBoundingClientRect();
    return {
      x: clamp(((clientX - r.left) / r.width) * 100, 0, 100),
      y: clamp(((clientY - r.top) / r.height) * 100, 0, 100),
    };
  };
  const overFace = (clientX, clientY) => {
    const r = face.getBoundingClientRect();
    return clientX >= r.left && clientX <= r.right && clientY >= r.top && clientY <= r.bottom;
  };

  /* ---------- rendering ---------- */

  function render(item) {
    item.el.style.left = `${item.x}%`;
    item.el.style.top = `${item.y}%`;
    item.el.style.width = `${item.w}%`;
  }

  function select(name) {
    selected = name;
    Object.entries(placed).forEach(([n, item]) => item.el.classList.toggle('is-selected', n === name));
  }

  function updateUI() {
    const hasTika = Boolean(placed.tika);
    const hasJamara = Boolean(placed.jamara);
    const any = hasTika || hasJamara;

    doneBtn.disabled = !(hasTika && hasJamara);
    sizeUp.disabled = sizeDown.disabled = startOver.disabled = !any;

    document.querySelectorAll('[data-tray]').forEach((btn) => {
      btn.classList.toggle('is-placed', Boolean(placed[btn.dataset.tray]));
    });

    if (hasTika && hasJamara) hint.textContent = 'Perfect! Adjust if you like, then press Done.';
    else if (hasTika) hint.textContent = 'Nice! Now add the jamara.';
    else if (hasJamara) hint.textContent = 'Now add the tika on the forehead.';
    else hint.textContent = 'Drag them onto the face, or just tap them.';
  }

  /* ---------- placing / moving / removing ---------- */

  function place(name, x, y) {
    let item = placed[name];
    if (!item) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `placed placed-${name}`;
      button.setAttribute(
        'aria-label',
        `${DEFAULTS[name].label} on the face. Arrow keys move it, plus and minus resize it, Delete removes it.`
      );
      const img = document.createElement('img');
      img.src = SRC[name];
      img.alt = '';
      img.draggable = false;
      button.appendChild(img);
      face.appendChild(button);

      item = { el: button, x, y, w: DEFAULTS[name].w };
      placed[name] = item;

      button.addEventListener('pointerdown', (event) => startMove(event, name));
      button.addEventListener('keydown', (event) => onKey(event, name));
      button.addEventListener('focus', () => select(name));
    }
    item.x = x;
    item.y = y;
    render(item);
    select(name);
    updateUI();
  }

  function remove(name) {
    const item = placed[name];
    if (!item) return;
    item.el.remove();
    delete placed[name];
    if (selected === name) selected = null;
    updateUI();
  }

  function resize(name, factor) {
    const item = placed[name];
    if (!item) return;
    const base = DEFAULTS[name].w;
    item.w = clamp(item.w * factor, base * 0.4, base * 2.5);
    render(item);
  }

  function currentTarget() {
    return selected && placed[selected] ? selected : Object.keys(placed)[0] || null;
  }

  function startMove(event, name) {
    if (event.button !== 0) return;
    event.preventDefault(); // no text selection / native image drag
    const item = placed[name];
    const el = item.el;
    select(name);
    el.focus({ preventScroll: true });
    el.setPointerCapture(event.pointerId);

    // Remember where inside the item the pointer grabbed it, so it doesn't jump to the pointer.
    const start = toPercent(event.clientX, event.clientY);
    const grabX = start.x - item.x;
    const grabY = start.y - item.y;

    const move = (ev) => {
      const p = toPercent(ev.clientX, ev.clientY);
      item.x = clamp(p.x - grabX, 0, 100);
      item.y = clamp(p.y - grabY, 0, 100);
      render(item);
    };
    const end = () => {
      el.removeEventListener('pointermove', move);
      el.removeEventListener('pointerup', end);
      el.removeEventListener('pointercancel', end);
    };
    el.addEventListener('pointermove', move);
    el.addEventListener('pointerup', end);
    el.addEventListener('pointercancel', end);
  }

  function onKey(event, name) {
    const item = placed[name];
    const step = event.shiftKey ? 5 : 1;
    switch (event.key) {
      case 'ArrowLeft': item.x = clamp(item.x - step, 0, 100); break;
      case 'ArrowRight': item.x = clamp(item.x + step, 0, 100); break;
      case 'ArrowUp': item.y = clamp(item.y - step, 0, 100); break;
      case 'ArrowDown': item.y = clamp(item.y + step, 0, 100); break;
      case '+': case '=': resize(name, SIZE_STEP); return event.preventDefault();
      case '-': case '_': resize(name, 1 / SIZE_STEP); return event.preventDefault();
      case 'Delete': case 'Backspace': remove(name); return event.preventDefault();
      default: return;
    }
    event.preventDefault();
    render(item);
  }

  /* ---------- the tray: drag out (pointer) or tap / Enter (click) ---------- */

  function makeGhost(name) {
    const ghost = document.createElement('img');
    ghost.src = SRC[name];
    ghost.alt = '';
    ghost.className = 'drag-ghost';
    const widthPct = placed[name] ? placed[name].w : DEFAULTS[name].w;
    ghost.style.width = `${(face.getBoundingClientRect().width * widthPct) / 100}px`;
    document.body.appendChild(ghost);
    return ghost;
  }

  document.querySelectorAll('[data-tray]').forEach((button) => {
    const name = button.dataset.tray;
    let drag = null;
    let suppressClick = false;

    button.addEventListener('pointerdown', (event) => {
      if (event.button !== 0) return;
      drag = { id: event.pointerId, sx: event.clientX, sy: event.clientY, moved: false, ghost: null };
      button.setPointerCapture(event.pointerId);
    });

    button.addEventListener('pointermove', (event) => {
      if (!drag || event.pointerId !== drag.id) return;
      if (!drag.moved) {
        if (Math.hypot(event.clientX - drag.sx, event.clientY - drag.sy) < DRAG_THRESHOLD) return;
        drag.moved = true;
        drag.ghost = makeGhost(name);
        button.classList.add('is-dragging');
      }
      drag.ghost.style.left = `${event.clientX}px`;
      drag.ghost.style.top = `${event.clientY}px`;
      face.classList.toggle('is-over', overFace(event.clientX, event.clientY));
    });

    const finish = (event, cancelled) => {
      if (!drag || event.pointerId !== drag.id) return;
      const wasDrag = drag.moved;
      if (drag.ghost) drag.ghost.remove();
      button.classList.remove('is-dragging');
      face.classList.remove('is-over');

      if (wasDrag) {
        // The browser still fires a click after a drag; don't let it also place the item.
        suppressClick = true;
        setTimeout(() => { suppressClick = false; }, 0);
        if (!cancelled && overFace(event.clientX, event.clientY)) {
          const p = toPercent(event.clientX, event.clientY);
          place(name, p.x, p.y);
        }
      }
      drag = null;
    };
    button.addEventListener('pointerup', (event) => finish(event, false));
    button.addEventListener('pointercancel', (event) => finish(event, true));

    // Tap, click or Enter/Space: drop it in its usual spot, ready to be nudged.
    button.addEventListener('click', () => {
      if (suppressClick) return;
      place(name, DEFAULTS[name].x, DEFAULTS[name].y);
    });
  });

  /* ---------- toolbar + Done ---------- */

  sizeUp.addEventListener('click', () => { const t = currentTarget(); if (t) resize(t, SIZE_STEP); });
  sizeDown.addEventListener('click', () => { const t = currentTarget(); if (t) resize(t, 1 / SIZE_STEP); });
  startOver.addEventListener('click', () => { Object.keys(placed).forEach(remove); });

  // Tapping the bare photo deselects, so the dashed "selected" outline doesn't linger.
  face.addEventListener('pointerdown', (event) => {
    if (event.target === face) select(null);
  });

  doneBtn.addEventListener('click', () => {
    if (doneBtn.disabled || !dialog || dialog.open) return;
    select(null); // show the finished face without the editing outline
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', ''); // very old browsers: show it non-modally
  });

  updateUI();
})();

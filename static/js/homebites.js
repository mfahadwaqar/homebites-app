/* Native links and forms remain available when JavaScript is disabled. */
(() => {
  const toggle = document.querySelector('.nav-toggle');
  const navigation = document.getElementById('main-navigation');
  if (!toggle || !navigation) return;

  const compact = window.matchMedia('(max-width: 70rem)');
  const setOpen = (open, restoreFocus = false) => {
    toggle.setAttribute('aria-expanded', String(open));
    navigation.hidden = compact.matches && !open;
    if (restoreFocus) toggle.focus();
  };
  const syncLayout = () => {
    const focusWasInNavigation = navigation.contains(document.activeElement);
    toggle.hidden = !compact.matches;
    setOpen(false, compact.matches && focusWasInNavigation);
  };

  syncLayout();
  compact.addEventListener('change', syncLayout);
  toggle.addEventListener('click', () => {
    setOpen(toggle.getAttribute('aria-expanded') !== 'true');
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && compact.matches && !navigation.hidden) {
      setOpen(false, true);
    }
  });
  document.addEventListener('click', (event) => {
    if (!compact.matches || navigation.hidden) return;
    if (!event.target.closest('.site-header')) setOpen(false);
    else if (event.target.closest('#main-navigation a')) setOpen(false);
  });
  document.addEventListener('focusin', (event) => {
    if (compact.matches && !navigation.hidden && !event.target.closest('.site-header')) {
      setOpen(false);
    }
  });
})();

/* Payment hold countdown. The server still enforces the real expiry. */
(() => {
  const node = document.querySelector('.pay-countdown[data-expires]');
  if (!node) return;
  const target = node.querySelector('.pay-countdown__left');
  const expires = new Date(node.dataset.expires).getTime();
  if (!target || Number.isNaN(expires)) return;
  const tick = () => {
    const left = Math.max(0, Math.floor((expires - Date.now()) / 1000));
    target.textContent = left > 0 ? `Time left: ${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')}.` : 'The hold has expired. Refresh this page.';
    if (left > 0) setTimeout(tick, 1000);
  };
  tick();
})();

/* Update the delivery price as soon as the delivery choice is complete. */
(() => {
  const method = document.getElementById('method');
  const destination = document.getElementById('destination');
  if (!method || !destination || !method.form) return;
  const form = method.form;
  const button = form.querySelector('.js-hide-when-auto');
  if (button) button.hidden = true;
  try {
    const y = sessionStorage.getItem('hb-cart-scroll');
    if (y !== null) { sessionStorage.removeItem('hb-cart-scroll'); window.scrollTo(0, Number(y)); }
  } catch (e) { /* storage unavailable: skip scroll restore */ }
  const hint = document.getElementById('delivery-hint');
  const update = () => {
    if (hint) hint.hidden = !(method.value === 'delivery' && !destination.value);
    if (method.value === 'delivery' && !destination.value) return;
    try { sessionStorage.setItem('hb-cart-scroll', String(window.scrollY)); } catch (e) { /* ignore */ }
    form.requestSubmit();
  };
  method.addEventListener('change', update);
  destination.addEventListener('change', update);
})();

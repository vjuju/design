/* Boutons gigot — comportement (voir gigot-boutons.css).
 *
 *   <link rel="stylesheet" href="gigot-boutons.css">
 *   <button class="g-btn" data-face="jaune" data-flanc="rose">Réserver</button>
 *   <button class="g-btn g-puce" data-flanc="vert" data-on="vert" aria-pressed="false">Plein air</button>
 *   <script src="gigot-boutons.js"></script>
 *   <script>GigotBoutons.init(document)</script>
 *
 * Survol           : la face suit un peu le curseur, le flanc reste en place.
 * aria-pressed     : le bouton devient un interrupteur ; un clic bascule l'état,
 *                    pose des traits de vibration et émet « change » (detail.checked).
 * .g-groupe[data-unique] : un seul bouton activé à la fois dans le groupe (jours).
 */
(function (global) {
  'use strict';

  // trois traits en haut à gauche, trois en bas à droite, rayonnant depuis le coin
  var RAYONS = [
    ['12px', '2px', '-14deg'], ['4px', '10px', '-45deg'], ['-1px', '22px', '-78deg'],
    ['calc(100% - 12px)', 'calc(100% - 2px)', '166deg'], ['calc(100% - 4px)', 'calc(100% - 10px)', '135deg'],
    ['calc(100% + 1px)', 'calc(100% - 22px)', '102deg']
  ];
  var reduit = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var tactile = global.matchMedia && global.matchMedia('(hover: none)').matches;

  function rayons(b) {
    if (b.querySelector('.g-rayons')) return;
    var s = document.createElement('span');
    s.className = 'g-rayons';
    s.setAttribute('aria-hidden', 'true');
    RAYONS.forEach(function (r) {
      var i = document.createElement('i');
      i.style.cssText = '--x:' + r[0] + ';--y:' + r[1] + ';--a:' + r[2];
      s.appendChild(i);
    });
    b.appendChild(s);
  }

  function regle(b, on, notifier) {
    if ((b.getAttribute('aria-pressed') === 'true') === on) return;
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    if (notifier) b.dispatchEvent(new CustomEvent('change', { bubbles: true, detail: { checked: on } }));
  }

  function prepare(b) {
    if (b.dataset.gigot) return;
    b.dataset.gigot = '1';

    if (!reduit && !tactile) {
      b.addEventListener('pointermove', function (e) {
        var r = b.getBoundingClientRect();
        var dx = (e.clientX - r.left) / r.width - 0.5, dy = (e.clientY - r.top) / r.height - 0.5;
        b.style.setProperty('--fx', (dx * 5).toFixed(1) + 'px');
        b.style.setProperty('--fy', (dy * 4).toFixed(1) + 'px');
      });
      b.addEventListener('pointerleave', function () {
        b.style.removeProperty('--fx');
        b.style.removeProperty('--fy');
      });
    }

    if (!b.hasAttribute('aria-pressed')) return;
    rayons(b);
    b.addEventListener('click', function () {
      var groupe = b.closest('.g-groupe[data-unique]');
      if (groupe) {
        if (b.getAttribute('aria-pressed') === 'true') return;   // un jour reste toujours choisi
        groupe.querySelectorAll('.g-btn[aria-pressed="true"]').forEach(function (o) { regle(o, false, true); });
        regle(b, true, true);
        return;
      }
      regle(b, b.getAttribute('aria-pressed') !== 'true', true);
    });
  }

  function init(racine) {
    (racine || document).querySelectorAll('.g-btn').forEach(prepare);
  }

  global.GigotBoutons = { init: init, regle: function (b, on) { regle(b, !!on, false); } };
})(window);

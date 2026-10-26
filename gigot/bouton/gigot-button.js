/* Bouton gigot — version sans framework.
 *
 *   <link rel="stylesheet" href="gigot-button.css">
 *   <script src="gigot-button.js"></script>
 *   var b = GigotButton.create({ fond: 'rose', face: 'cyan', flanc: 'violet', label: 'Suivre' });
 *   b.addEventListener('change', function (e) { console.log(e.detail.checked); });
 *   document.body.appendChild(b);
 *
 * Survol (non coché) : la face du O suit le curseur, les arcs pivotent à 90° de l'axe centre → curseur
 *                      et gardent leur position quand le curseur sort.
 * Clic (coché)       : la face rejoint le flanc, un seul rond recentré rebondit, les arcs deviennent
 *                      des paupières depuis leur angle courant, des traits rayonnent dans le O ;
 *                      la pupille et les traits suivent alors le curseur.
 * Re-clic            : tout revient. L'état est exposé par aria-pressed et l'évènement « change ».
 */
(function (global) {
  'use strict';

  var C = { noir: '#111111', blanc: '#FFFFFF', rose: '#FF3EA5', jaune: '#FFD60A',
            violet: '#7B2FF7', cyan: '#2EC4F1', vert: '#39D353', orange: '#FF6A13' };
  var ARC_ANGLE = 225;                                   // milieu de l'arc 1 au repos (haut gauche)
  var OEIL_R = 76.9, OEIL_DEMI = 48, OEIL_HAUT = 18;     // paupières : plus plates qu'un cercle
  var DUREE = 600;                                       // ms, transition arcs ↔ paupières

  function lerp(a, b, t) { return a + (b - a) * t; }
  function proche(angle, ref) { return ref + (((angle - ref) % 360 + 540) % 360 - 180); }
  function tourne(x, y, deg) {
    var a = deg * Math.PI / 180, dx = x - 80, dy = y - 80;
    return [80 + dx * Math.cos(a) - dy * Math.sin(a), 80 + dx * Math.sin(a) + dy * Math.cos(a)];
  }
  function arc(cx, cy, R, milieu, demi) {
    var a = (milieu - demi) * Math.PI / 180, b = (milieu + demi) * Math.PI / 180;
    return 'M' + (cx + R * Math.cos(a)).toFixed(1) + ' ' + (cy + R * Math.sin(a)).toFixed(1) +
           'A' + R.toFixed(1) + ' ' + R.toFixed(1) + ' 0 0 1 ' +
           (cx + R * Math.cos(b)).toFixed(1) + ' ' + (cy + R * Math.sin(b)).toFixed(1);
  }

  function svg(fond, face, flanc) {
    // encre (arcs) blanche seulement sur les fonds sombres — contraste ≥ 4,5:1
    var encre = (fond === 'noir' || fond === 'violet') ? C.blanc : C.noir;
    var rayons = '';
    for (var i = 0; i < 8; i++) {
      rayons += '<line class="rayon" style="--a:' + (i * 45 + 22.5) + 'deg" x1="101" y1="80" x2="108" y2="80"></line>';
    }
    return '<svg viewBox="0 0 160 160" aria-hidden="true">' +
      '<rect width="160" height="160" fill="' + C[fond] + '"></rect>' +
      '<g class="arcs" fill="none" stroke="' + encre + '" stroke-width="7" stroke-linecap="round">' +
        '<path class="arc" d="' + arc(73, 73, 60, 225, 25) + '"></path>' +
        '<path class="arc" d="' + arc(87, 87, 60, 45, 25) + '"></path>' +
      '</g>' +
      '<g class="iris">' +
        '<circle class="flanc" cx="87" cy="87" r="46" fill="' + C[flanc] + '" stroke="#111111" stroke-width="7"></circle>' +
        '<g class="face">' +
          '<circle cx="73" cy="73" r="46" fill="' + C[face] + '" stroke="#111111" stroke-width="7"></circle>' +
          '<circle class="pupille" cx="73" cy="73" r="13" fill="#111111"></circle>' +
        '</g>' +
        '<g class="pupille" stroke="#111111" stroke-width="4" stroke-linecap="round">' + rayons + '</g>' +
      '</g>' +
    '</svg>';
  }

  function create(opts) {
    opts = opts || {};
    var fond = opts.fond || 'rose', face = opts.face || 'cyan', flanc = opts.flanc || 'violet';
    var reduit = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches;

    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'gigot-btn';
    if (opts.taille) b.style.setProperty('--taille', opts.taille + 'px');
    b.setAttribute('aria-label', opts.label || 'gigot');
    b.setAttribute('aria-pressed', 'false');
    b.innerHTML = svg(fond, face, flanc);

    var arcs = b.querySelectorAll('.arc');
    var rot = 0, rotC = 0, t = 0, anim = 0;

    function tourneVers(cible) {
      rot += ((cible - rot) % 360 + 540) % 360 - 180;     // chemin le plus court
      b.style.setProperty('--rot', rot.toFixed(1) + 'deg');
    }
    function dessine(t) {
      var R = lerp(60, OEIL_R, t), demi = lerp(25, OEIL_DEMI, t);
      var haut = tourne(80, OEIL_HAUT + OEIL_R, -rotC);
      var bas = tourne(80, 160 - OEIL_HAUT - OEIL_R, -rotC);
      // chaque arc rejoint la paupière la plus proche pour tourner le moins possible
      var a1 = proche(270 - rotC, 225), b1 = proche(90 - rotC, 225);
      var versHaut = Math.abs(a1 - 225) <= Math.abs(b1 - 225);
      var p1 = versHaut ? haut : bas, p2 = versHaut ? bas : haut;
      var m1 = versHaut ? a1 : b1, m2 = proche(m1 - 180, 45);
      arcs[0].setAttribute('d', arc(lerp(73, p1[0], t), lerp(73, p1[1], t), R, lerp(225, m1, t), demi));
      arcs[1].setAttribute('d', arc(lerp(87, p2[0], t), lerp(87, p2[1], t), R, lerp(45, m2, t), demi));
    }
    function anime(vers) {
      cancelAnimationFrame(anim);
      if (reduit) { t = vers; dessine(t); return; }
      var depart = t, t0 = null;
      function pas(ts) {
        if (t0 === null) t0 = ts;
        var k = Math.min(1, (ts - t0) / DUREE);
        var e = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
        t = depart + (vers - depart) * e;
        dessine(t);
        if (k < 1) anim = requestAnimationFrame(pas);
      }
      anim = requestAnimationFrame(pas);
    }

    if (!reduit) {
      b.addEventListener('pointermove', function (e) {
        var r = b.getBoundingClientRect();
        var dx = (e.clientX - r.left) / r.width - 0.5;   // -0,5 → 0,5
        var dy = (e.clientY - r.top) / r.height - 0.5;
        if (b.classList.contains('coche')) {               // l'œil regarde le curseur
          b.style.setProperty('--px', (dx * 20).toFixed(1) + 'px');
          b.style.setProperty('--py', (dy * 20).toFixed(1) + 'px');
          return;
        }
        b.style.setProperty('--fx', (dx * 16).toFixed(1) + 'px');
        b.style.setProperty('--fy', (dy * 16).toFixed(1) + 'px');
        if (Math.abs(dx) + Math.abs(dy) > 0.04) {
          tourneVers(Math.atan2(dy, dx) * 180 / Math.PI + 90 - ARC_ANGLE);
        }
      });
    }

    function regle(coche, notifier) {
      if (coche === b.classList.contains('coche')) return;
      if (coche) rotC = rot;           // l'œil se forme depuis l'orientation courante des arcs
      else { b.style.setProperty('--px', '0px'); b.style.setProperty('--py', '0px'); }
      anime(coche ? 1 : 0);
      b.classList.toggle('coche', coche);
      b.setAttribute('aria-pressed', coche ? 'true' : 'false');
      if (notifier) b.dispatchEvent(new CustomEvent('change', { detail: { checked: coche } }));
    }
    b.addEventListener('click', function () { regle(!b.classList.contains('coche'), true); });

    Object.defineProperty(b, 'checked', {
      get: function () { return b.classList.contains('coche'); },
      set: function (v) { regle(!!v, false); }
    });
    if (opts.checked) regle(true, false);
    return b;
  }

  global.GigotButton = { create: create, couleurs: C };
})(window);

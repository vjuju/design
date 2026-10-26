/*
 * aplats.js — figures.py rejoué par le navigateur, et animé.
 *
 * Version gigot de photo/aplats/web/aplats.js : contours en noir gigot
 * (#111111), palette gigot par défaut (`vive`). Le reste est identique.
 *
 * Même chaîne que figures.py, sans IA ni bibliothèque :
 *   1. analyse sur une copie de 256 px : carte de saillance (écart à la
 *      couleur dominante, contraste local, saturation, biais central), seuil
 *      d'Otsu, composantes connexes classées par saillance ;
 *   2. silhouette « au pinceau » (fermeture au flou gaussien, trous bouchés),
 *      élargie, contour suivi pixel par pixel, réduit par Douglas-Peucker,
 *      relié par une Catmull-Rom centripète ;
 *   3. aplat de couleur, gros trait noir, vibrations (arcs aux angles,
 *      traits droits ailleurs) autour du sujet principal. La photo reste
 *      visible sous l'aplat ; l'option `fill` choisit comment (voir FILLS) :
 *      par défaut, multiply sur fond clair et screen sur fond sombre.
 *      L'option `palette` choisit les couleurs (voir PALETTES).
 *
 * Ce que le script Python ne fait pas : les formes sont vivantes. Chaque
 * courbe est une chaîne de points montés sur ressorts. Le curseur les
 * repousse (la forme se creuse et glisse pour l'éviter) ; un clic envoie une
 * forme vers une autre zone saillante de la photo, dont elle prend la
 * silhouette en se déformant.
 *
 *     <img src="photo.jpg" data-aplats>
 *     <script src="aplats.js"></script>      // tout img[data-aplats]
 *     Aplats.attach(img, { seed: 7, fill: 'trame', palette: 'pop' })  // ou à la main
 *
 * Les images doivent venir de la même origine que la page (le navigateur
 * refuse sinon de lire leurs pixels) : servir le dossier en http, pas en
 * file://.
 */
(function () {
  'use strict';

  // ------------------------------------------------------------------------
  // Palettes
  // ------------------------------------------------------------------------

  const FOND = '#F8F8F8';
  const CONTOUR = '#111111';   // noir gigot : contours toujours noirs
  const PALETTES = {
    // Les six couleurs flash de gigot (tokens.css), la palette par défaut.
    vive: {
      rose: '#FF3EA5',
      jaune: '#FFD60A',
      violet: '#7B2FF7',
      cyan: '#2EC4F1',
      vert: '#39D353',
      orange: '#FF6A13',
    },
    // Celle de pop.py, plus douce.
    pop: {
      jaune: '#F4C946',
      vert: '#6AB357',
      rose: '#DB6DA2',
      orange: '#E26E3B',
      bleu: '#53B5E3',
    },
  };

  const ANALYSIS_SIZE = 256;
  const N = 160;            // points par courbe animée
  const ZONES = 8;          // zones saillantes retenues : 3 formes, le reste en réserve

  const reduceMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Hasard reproductible (mulberry32) : une graine redonne le même tirage.
  function random(seed) {
    let a = seed >>> 0;
    const next = () => {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    next.uniform = (lo, hi) => lo + (hi - lo) * next();
    next.shuffle = (arr) => {
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(next() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
      }
      return arr;
    };
    return next;
  }

  // ------------------------------------------------------------------------
  // Flou gaussien (trois flous de boîte, comme Pillow) et morphologie
  //
  // Dilater, éroder, lisser : on floute le masque puis on le re-seuille ; les
  // bords sortent ronds, comme tracés au pinceau.
  // ------------------------------------------------------------------------

  function boxSizes(sigma) {
    let wl = Math.floor(Math.sqrt(12 * sigma * sigma / 3 + 1));
    if (wl % 2 === 0) wl--;
    const m = Math.round((12 * sigma * sigma - 3 * wl * wl - 12 * wl - 9) / (-4 * wl - 4));
    return [0, 1, 2].map((i) => (i < m ? wl : wl + 2));
  }

  function boxPass(src, dst, w, h, r, horizontal) {
    const len = horizontal ? w : h;
    const lines = horizontal ? h : w;
    const step = horizontal ? 1 : w;
    const norm = 1 / (2 * r + 1);
    for (let l = 0; l < lines; l++) {
      const base = horizontal ? l * w : l;
      const at = (i) => src[base + (i < 0 ? 0 : i >= len ? len - 1 : i) * step];
      let acc = 0;
      for (let i = -r; i <= r; i++) acc += at(i);
      for (let i = 0; i < len; i++) {
        dst[base + i * step] = acc * norm;
        acc += at(i + r + 1) - at(i - r);
      }
    }
  }

  function blur(src, w, h, sigma) {
    if (sigma <= 0) return Float32Array.from(src);
    let a = Float32Array.from(src);
    let b = new Float32Array(a.length);
    if (sigma < 1.5) {
      // Petit rayon : noyau gaussien exact, les boîtes seraient trop grossières.
      const r = Math.ceil(3 * sigma);
      const k = [];
      let sum = 0;
      for (let i = -r; i <= r; i++) { k.push(Math.exp(-i * i / (2 * sigma * sigma))); sum += k[k.length - 1]; }
      for (const horizontal of [true, false]) {
        const len = horizontal ? w : h;
        for (let y = 0; y < h; y++) {
          for (let x = 0; x < w; x++) {
            let acc = 0;
            const p = horizontal ? x : y;
            for (let i = -r; i <= r; i++) {
              let q = p + i;
              q = q < 0 ? 0 : q >= len ? len - 1 : q;
              acc += k[i + r] * (horizontal ? a[y * w + q] : a[q * w + x]);
            }
            b[y * w + x] = acc / sum;
          }
        }
        [a, b] = [b, a];
      }
      return a;
    }
    for (const size of boxSizes(sigma)) {
      const r = (size - 1) >> 1;
      boxPass(a, b, w, h, r, true);
      boxPass(b, a, w, h, r, false);
    }
    return a;
  }

  const above = (f, t) => { const m = new Uint8Array(f.length); for (let i = 0; i < f.length; i++) m[i] = f[i] > t ? 1 : 0; return m; };
  const asFloat = (m) => Float32Array.from(m);

  function dilate(m, w, h, d) {
    return d <= 0.5 ? m.slice() : above(blur(asFloat(m), w, h, d / 1.4), 0.08);
  }

  function erode(m, w, h, d) {
    return d <= 0.5 ? m.slice() : above(blur(asFloat(m), w, h, d / 1.4), 0.92);
  }

  function smooth(m, w, h, r) {
    return above(blur(asFloat(m), w, h, r), 0.5);
  }

  // Composantes connexes (4-voisinage), de la plus grande à la plus petite.
  function components(m, w, h, minArea) {
    const seen = new Uint8Array(m.length);
    const stack = new Int32Array(m.length);
    const parts = [];
    for (let s = 0; s < m.length; s++) {
      if (!m[s] || seen[s]) continue;
      const mask = new Uint8Array(m.length);
      let top = 0, area = 0;
      stack[top++] = s; seen[s] = 1;
      while (top) {
        const i = stack[--top];
        mask[i] = 1; area++;
        const x = i % w, y = (i - x) / w;
        if (x > 0 && m[i - 1] && !seen[i - 1]) { seen[i - 1] = 1; stack[top++] = i - 1; }
        if (x < w - 1 && m[i + 1] && !seen[i + 1]) { seen[i + 1] = 1; stack[top++] = i + 1; }
        if (y > 0 && m[i - w] && !seen[i - w]) { seen[i - w] = 1; stack[top++] = i - w; }
        if (y < h - 1 && m[i + w] && !seen[i + w]) { seen[i + w] = 1; stack[top++] = i + w; }
      }
      if (area >= minArea) parts.push({ mask, area });
    }
    return parts.sort((a, b) => b.area - a.area);
  }

  // Bouche les trous : tout ce qui n'est pas relié au bord du cadre.
  function fillHoles(m, w, h) {
    const out = new Uint8Array(m.length).fill(1);
    const stack = [];
    const push = (i) => { if (!m[i] && out[i]) { out[i] = 0; stack.push(i); } };
    for (let x = 0; x < w; x++) { push(x); push((h - 1) * w + x); }
    for (let y = 0; y < h; y++) { push(y * w); push(y * w + w - 1); }
    while (stack.length) {
      const i = stack.pop();
      const x = i % w, y = (i - x) / w;
      if (x > 0) push(i - 1);
      if (x < w - 1) push(i + 1);
      if (y > 0) push(i - w);
      if (y < h - 1) push(i + w);
    }
    for (let i = 0; i < m.length; i++) out[i] = out[i] || m[i];
    return out;
  }

  // La silhouette « au pinceau » : fermeture, lissage, trous bouchés.
  function boldShape(m, w, h, d) {
    const r = 0.035 * d;
    const closed = erode(dilate(m, w, h, r), w, h, r * 0.8);
    for (let i = 0; i < m.length; i++) closed[i] = closed[i] || m[i];
    return fillHoles(smooth(closed, w, h, 0.008 * d), w, h);
  }

  // ------------------------------------------------------------------------
  // Détection du sujet
  // ------------------------------------------------------------------------

  function percentiles(x, ps) {
    const s = Float32Array.from(x).sort();
    return ps.map((p) => {
      const pos = p / 100 * (s.length - 1);
      const i = Math.floor(pos);
      return s[i] + (s[Math.min(i + 1, s.length - 1)] - s[i]) * (pos - i);
    });
  }

  // Étirement par percentiles : la « montée de contraste ».
  function normalize(x, lo = 2, hi = 98) {
    const [a, b] = percentiles(x, [lo, hi]);
    const out = new Float32Array(x.length);
    if (b - a < 1e-6) return out;
    for (let i = 0; i < x.length; i++) out[i] = Math.min(1, Math.max(0, (x[i] - a) / (b - a)));
    return out;
  }

  function otsu(x) {
    const hist = new Float64Array(256);
    for (const v of x) hist[Math.min(255, Math.max(0, Math.floor(v * 256)))]++;
    let omega = 0, mu = 0, muT = 0;
    for (let i = 0; i < 256; i++) muT += i * hist[i] / x.length;
    let best = 0, at = 0;
    for (let i = 0; i < 256; i++) {
      omega += hist[i] / x.length;
      mu += i * hist[i] / x.length;
      const sigma = (muT * omega - mu) ** 2 / (omega * (1 - omega));
      if (sigma > best) { best = sigma; at = i; }
    }
    return at / 256;
  }

  // La couleur la plus répandue : sur la plupart des photos, c'est le fond.
  function dominant(img) {
    const { r, g, b } = img;
    const keys = new Uint16Array(r.length);
    const counts = new Uint32Array(512);
    const q = (v) => Math.min(7, Math.floor(v * 8));
    for (let i = 0; i < r.length; i++) {
      keys[i] = (q(r[i]) * 8 + q(g[i])) * 8 + q(b[i]);
      counts[keys[i]]++;
    }
    let top = 0;
    for (let k = 1; k < 512; k++) if (counts[k] > counts[top]) top = k;
    const mean = [0, 0, 0];
    for (let i = 0; i < r.length; i++) {
      if (keys[i] === top) { mean[0] += r[i]; mean[1] += g[i]; mean[2] += b[i]; }
    }
    return mean.map((v) => v / counts[top]);
  }

  // Carte de « ce qui se détache », entre 0 et 1 (voir pop.saliency).
  function saliency(img) {
    const { w, h, r, g, b, lum } = img;
    const d = Math.hypot(w, h);
    const bg = dominant(img);
    const dBg = new Float32Array(r.length);
    const sat = new Float32Array(r.length);
    for (let i = 0; i < r.length; i++) {
      dBg[i] = Math.hypot(r[i] - bg[0], g[i] - bg[1], b[i] - bg[2]);
      sat[i] = Math.max(r[i], g[i], b[i]) - Math.min(r[i], g[i], b[i]);
    }
    const far = blur(lum, w, h, 0.06 * d);
    const local = new Float32Array(r.length);
    for (let i = 0; i < r.length; i++) local[i] = Math.abs(lum[i] - far[i]);

    const nb = normalize(dBg), nl = normalize(local), ns = normalize(sat);
    const s = new Float32Array(r.length);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x;
        const c = Math.exp(-((x / w - 0.5) ** 2 + (y / h - 0.5) ** 2) / (2 * 0.33 ** 2));
        s[i] = (0.45 * nb[i] + 0.35 * nl[i] + 0.20 * ns[i]) * (0.55 + 0.45 * c);
      }
    }
    return normalize(blur(s, w, h, 0.006 * d), 1, 99.5);
  }

  // Les zones saillantes, de la plus importante à la moins importante.
  function subjects(img, maxCount, s = saliency(img)) {
    const { w, h } = img;
    const d = Math.hypot(w, h);
    const m = smooth(above(s, Math.max(otsu(s), 0.4)), w, h, 0.006 * d);
    const parts = components(m, w, h, Math.floor(0.002 * m.length));
    for (const p of parts) {
      let sum = 0, x0 = w, y0 = h, x1 = 0, y1 = 0;
      for (let i = 0; i < p.mask.length; i++) {
        if (!p.mask[i]) continue;
        sum += s[i];
        const x = i % w, y = (i - x) / w;
        if (x < x0) x0 = x; if (x > x1) x1 = x;
        if (y < y0) y0 = y; if (y > y1) y1 = y;
      }
      const touches = (y0 === 0) + (x0 === 0) + (y1 === h - 1) + (x1 === w - 1);
      p.score = sum * 0.5 ** touches;
    }
    return parts.sort((a, b) => b.score - a.score).slice(0, maxCount);
  }

  // ------------------------------------------------------------------------
  // Formes vectorielles : contour, points de passage, courbe lisse
  // ------------------------------------------------------------------------

  const DIRS = [[1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1]];
  const DIR_INDEX = {};
  DIRS.forEach(([dx, dy], i) => { DIR_INDEX[dx + ',' + dy] = i; });

  // Contour extérieur d'un masque d'un seul tenant (suivi de Moore).
  function traceContour(m, w, h) {
    const W = w + 2, H = h + 2;
    const p = new Uint8Array(W * H);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) p[(y + 1) * W + x + 1] = m[y * w + x];
    let start = p.indexOf(1);
    if (start < 0) return [];
    let cx = start % W, cy = (start - cx) / W;
    const sx = cx, sy = cy;
    let back = 4;                                   // on arrive par la gauche
    const pts = [[cx - 1, cy - 1]];
    for (let it = 0; it < 4 * p.length; it++) {
      let moved = false;
      for (let k = 1; k <= 8; k++) {
        const nd = (back + k) % 8;
        const nx = cx + DIRS[nd][0], ny = cy + DIRS[nd][1];
        if (p[ny * W + nx]) {
          const bd = DIRS[(back + k - 1) % 8];
          back = DIR_INDEX[(cx + bd[0] - nx) + ',' + (cy + bd[1] - ny)];
          cx = nx; cy = ny; moved = true;
          break;
        }
      }
      if (!moved || (cx === sx && cy === sy)) break;
      pts.push([cx - 1, cy - 1]);
    }
    return pts;
  }

  function rdp(pts, tol) {
    const keep = new Uint8Array(pts.length);
    keep[0] = keep[pts.length - 1] = 1;
    const stack = [[0, pts.length - 1]];
    while (stack.length) {
      const [i, j] = stack.pop();
      if (j <= i + 1) continue;
      const [ax, ay] = pts[i], [bx, by] = pts[j];
      const n = Math.hypot(bx - ax, by - ay) || 1;
      let best = -1, at = 0;
      for (let q = i + 1; q < j; q++) {
        const dist = Math.abs((bx - ax) * (pts[q][1] - ay) - (by - ay) * (pts[q][0] - ax)) / n;
        if (dist > best) { best = dist; at = q; }
      }
      if (best > tol) { keep[at] = 1; stack.push([i, at], [at, j]); }
    }
    return pts.filter((_, i) => keep[i]);
  }

  // Les quelques points de passage d'un contour fermé (Douglas-Peucker).
  function keyPoints(pts, tol, minPoints = 5) {
    let far = 0, best = -1;
    pts.forEach(([x, y], i) => {
      const dd = Math.hypot(x - pts[0][0], y - pts[0][1]);
      if (dd > best) { best = dd; far = i; }
    });
    for (;;) {
      const a = rdp(pts.slice(0, far + 1), tol);
      const b = rdp(pts.slice(far).concat([pts[0]]), tol);
      const keys = a.slice(0, -1).concat(b.slice(0, -1));
      if (keys.length >= minPoints || tol < 0.5) return keys;
      tol /= 1.6;
    }
  }

  // Courbe fermée lisse passant par les points clés (Catmull-Rom centripète).
  function spline(keys, samples = 24) {
    const out = [];
    const n = keys.length;
    const lerp = (p, q, ta, tb, t) => [
      ((tb - t) * p[0] + (t - ta) * q[0]) / (tb - ta),
      ((tb - t) * p[1] + (t - ta) * q[1]) / (tb - ta),
    ];
    for (let i = 0; i < n; i++) {
      const p0 = keys[(i - 1 + n) % n], p1 = keys[i], p2 = keys[(i + 1) % n], p3 = keys[(i + 2) % n];
      const t0 = 0;
      const t1 = t0 + Math.max(Math.hypot(p1[0] - p0[0], p1[1] - p0[1]), 1e-6) ** 0.5;
      const t2 = t1 + Math.max(Math.hypot(p2[0] - p1[0], p2[1] - p1[1]), 1e-6) ** 0.5;
      const t3 = t2 + Math.max(Math.hypot(p3[0] - p2[0], p3[1] - p2[1]), 1e-6) ** 0.5;
      for (let s = 0; s < samples; s++) {
        const t = t1 + (t2 - t1) * s / samples;
        const a1 = lerp(p0, p1, t0, t1, t), a2 = lerp(p1, p2, t1, t2, t), a3 = lerp(p2, p3, t2, t3, t);
        const b1 = lerp(a1, a2, t0, t2, t), b2 = lerp(a2, a3, t1, t3, t);
        out.push(lerp(b1, b2, t1, t2, t));
      }
    }
    return out;
  }

  // Courbe fermée -> `count` points également espacés, sens trigonométrique
  // à l'écran : toutes les courbes tournent dans le même sens, on peut donc
  // passer de l'une à l'autre point par point.
  function evenly(pts, count) {
    const n = pts.length;
    const cum = [0];
    for (let i = 1; i <= n; i++) {
      const a = pts[i - 1], b = pts[i % n];
      cum.push(cum[i - 1] + Math.hypot(b[0] - a[0], b[1] - a[1]));
    }
    const total = cum[n];
    const out = new Float32Array(2 * count);
    let j = 0;
    for (let k = 0; k < count; k++) {
      const at = total * k / count;
      while (cum[j + 1] < at) j++;
      const f = (at - cum[j]) / ((cum[j + 1] - cum[j]) || 1);
      const a = pts[j], b = pts[(j + 1) % n];
      out[2 * k] = a[0] + (b[0] - a[0]) * f;
      out[2 * k + 1] = a[1] + (b[1] - a[1]) * f;
    }
    if (area(out) < 0) {
      for (let k = 1; k < count - k; k++) {
        const q = count - k;
        [out[2 * k], out[2 * q]] = [out[2 * q], out[2 * k]];
        [out[2 * k + 1], out[2 * q + 1]] = [out[2 * q + 1], out[2 * k + 1]];
      }
    }
    return out;
  }

  function area(c) {
    const n = c.length / 2;
    let s = 0;
    for (let i = 0; i < n; i++) {
      const j = (i + 1) % n;
      s += c[2 * i] * c[2 * j + 1] - c[2 * j] * c[2 * i + 1];
    }
    return s / 2;
  }

  function centroid(c) {
    const n = c.length / 2;
    let x = 0, y = 0;
    for (let i = 0; i < n; i++) { x += c[2 * i]; y += c[2 * i + 1]; }
    return [x / n, y / n];
  }

  // Masque (copie réduite) -> courbe lisse en coordonnées de la photo.
  // Seule la plus grande partie du masque est gardée : une forme, un trait.
  function curveOf(m, w, h, scale, tol) {
    const parts = components(m, w, h, 4);
    if (!parts.length) return null;
    const pts = traceContour(parts[0].mask, w, h);
    if (pts.length < 8) return null;
    const curve = spline(keyPoints(pts, tol)).map(([x, y]) => [(x + 0.5) * scale, (y + 0.5) * scale]);
    return evenly(curve, N);
  }

  // Décale la courbe `to` d'un nombre de points tel qu'elle soit au plus près
  // de `from`, une fois les deux centrées : la métamorphose ne vrille pas.
  function align(from, to) {
    const [fx, fy] = centroid(from), [tx, ty] = centroid(to);
    let best = Infinity, shift = 0;
    for (let s = 0; s < N; s++) {
      let e = 0;
      for (let i = 0; i < N && e < best; i++) {
        const j = (i + s) % N;
        e += (from[2 * i] - fx - to[2 * j] + tx) ** 2 + (from[2 * i + 1] - fy - to[2 * j + 1] + ty) ** 2;
      }
      if (e < best) { best = e; shift = s; }
    }
    const out = new Float32Array(2 * N);
    for (let i = 0; i < N; i++) {
      const j = (i + shift) % N;
      out[2 * i] = to[2 * j];
      out[2 * i + 1] = to[2 * j + 1];
    }
    return out;
  }

  // Une courbe réduite à son centre : un trou de surface nulle.
  function collapsed(c) {
    const [x, y] = centroid(c);
    const out = new Float32Array(2 * N);
    for (let i = 0; i < N; i++) { out[2 * i] = x; out[2 * i + 1] = y; }
    return out;
  }

  function translated(c, dx, dy) {
    const out = Float32Array.from(c);
    for (let i = 0; i < N; i++) { out[2 * i] += dx; out[2 * i + 1] += dy; }
    return out;
  }

  function inside(c, x, y) {
    const n = c.length / 2;
    let hit = false;
    for (let i = 0, j = n - 1; i < n; j = i++) {
      const xi = c[2 * i], yi = c[2 * i + 1], xj = c[2 * j], yj = c[2 * j + 1];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) hit = !hit;
    }
    return hit;
  }

  // ------------------------------------------------------------------------
  // Vibrations (voir pop.vibrations)
  // ------------------------------------------------------------------------

  // Points espacés de `step` le long de la courbe, avec la normale sortante.
  function frameOf(c, step) {
    const n0 = c.length / 2;
    const cum = new Float32Array(n0 + 1);
    for (let i = 1; i <= n0; i++) {
      const a = i - 1, b = i % n0;
      cum[i] = cum[i - 1] + Math.hypot(c[2 * b] - c[2 * a], c[2 * b + 1] - c[2 * a + 1]);
    }
    const n = Math.max(1, Math.floor(cum[n0] / step));
    const pts = new Float32Array(2 * n);
    let j = 0;
    for (let k = 0; k < n; k++) {
      const at = k * step;
      while (cum[j + 1] < at) j++;
      const f = (at - cum[j]) / ((cum[j + 1] - cum[j]) || 1);
      const a = j, b = (j + 1) % n0;
      pts[2 * k] = c[2 * a] + (c[2 * b] - c[2 * a]) * f;
      pts[2 * k + 1] = c[2 * a + 1] + (c[2 * b + 1] - c[2 * a + 1]) * f;
    }
    const sign = area(pts) > 0 ? 1 : -1;
    const tan = new Float32Array(2 * n), normal = new Float32Array(2 * n);
    for (let i = 0; i < n; i++) {
      const p = (i - 1 + n) % n, q = (i + 1) % n;
      const tx = pts[2 * q] - pts[2 * p], ty = pts[2 * q + 1] - pts[2 * p + 1];
      const l = Math.hypot(tx, ty) + 1e-9;
      tan[2 * i] = tx / l; tan[2 * i + 1] = ty / l;
      normal[2 * i] = ty / l * sign; normal[2 * i + 1] = -tx / l * sign;
    }
    return { pts, tan, normal, n, sign };
  }

  // Les angles les plus marqués (là où la courbe tourne le plus vite, côté
  // bombé), en fraction de la longueur : ils restent attachés à la forme
  // pendant qu'elle bouge.
  function pickCorners(c, v) {
    const { tan, n, sign } = frameOf(c, v.step);
    if (n < 12) return [];
    const k = Math.max(2, Math.floor(v.arc / 2 / v.step));
    const half = Math.max(3, Math.floor(v.arc / 2 / v.step));
    const turn = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const a = (i - k + n) % n, b = (i + k) % n;
      turn[i] = (tan[2 * a] * tan[2 * b + 1] - tan[2 * a + 1] * tan[2 * b]) * sign;
    }
    const order = Array.from(turn.keys()).sort((a, b) => turn[b] - turn[a]);
    const picked = [];
    for (const i of order) {
      if (picked.length === v.corners || turn[i] < 0.15) break;
      if (picked.every((j) => Math.min(Math.abs(i - j), n - Math.abs(i - j)) > 3 * half)) picked.push(i);
    }
    return picked.map((i) => i / n);
  }

  // Les traits de vibration, en polylignes à tracer à bouts ronds.
  function vibrationLines(c, v, corners) {
    const { pts, normal, n } = frameOf(c, v.step);
    if (n < 12) return [];
    const at = (i, g) => [pts[2 * i] + normal[2 * i] * g, pts[2 * i + 1] + normal[2 * i + 1] * g];
    const half = Math.max(3, Math.floor(v.arc / 2 / v.step));
    const margin = Math.floor(0.6 * v.spacing / v.step);
    const covered = new Uint8Array(n);
    const lines = [];
    for (const f of corners) {
      const i = Math.round(f * n) % n;
      for (let q = -half - margin; q <= half + margin; q++) covered[(i + q + n) % n] = 1;
      // Un arc contre l'angle, un second plus court et plus loin.
      for (const [g, span] of [[v.gap, half], [v.gap + 2.2 * v.width, Math.max(2, half >> 1)]]) {
        const line = [];
        for (let q = -span; q <= span; q++) line.push(at((i + q + n) % n, g));
        lines.push(line);
      }
    }
    const count = Math.max(4, Math.floor(n * v.step / v.spacing));
    const offset = Math.floor(v.offset * n);
    for (let k = 0; k < count; k++) {
      const i = (offset + Math.floor(k * n / count)) % n;
      if (covered[i]) continue;
      const L = v.length * (0.7 + 0.5 * v.rand[k % v.rand.length]);
      lines.push([at(i, v.gap), at(i, v.gap + L)]);
    }
    return lines;
  }

  // ------------------------------------------------------------------------
  // Une planche : une photo, son analyse, ses formes vivantes
  // ------------------------------------------------------------------------

  const active = new Set();
  let ticking = false;

  function wake(plate) {
    active.add(plate);
    if (!ticking) {
      ticking = true;
      let last = performance.now();
      const loop = (now) => {
        const dt = Math.min(0.033, (now - last) / 1000);
        last = now;
        for (const p of active) if (!p.step(dt)) active.delete(p);
        if (active.size) requestAnimationFrame(loop);
        else ticking = false;
      };
      requestAnimationFrame(loop);
    }
  }

  // Ressorts (unités : la diagonale de la photo, par seconde).
  const K = 70;            // raideur du retour au repos
  const DAMP = 9;          // amortissement : un peu de rebond, pas trop
  const NEIGHBOUR = 260;   // cohésion entre points voisins
  const REACH = 0.17;      // rayon d'action du curseur
  const PUSH = 0.07;       // creux maximal sous le curseur
  const DRIFT = 0.045;     // glissement maximal de toute la forme
  const INERTIA = 1.4;     // traîne pendant un déplacement
  const TRAVEL = 1.15;     // durée d'un déplacement, en secondes

  // Les façons de poser la couleur. Dans toutes, la photo reste visible sous
  // l'aplat. « Fond sombre » se mesure autour du sujet, comme pop.blend_for.
  const FILLS = {
    figures: 'multiply sur fond clair, halo sur fond sombre : le choix de figures.py',
    multiply: 'multiply partout : la couleur fonce la photo, qui transparaît',
    halo: 'halo partout : couleur couvrante autour du sujet, le sujet reste la photo',
    transparence: 'couleur posée à mi-opacité, sans mode de fusion',
    trame: 'hachures de couleur pleine : la photo intacte entre les traits',
    screen: 'multiply sur fond clair, screen sur fond sombre : la couleur éclaircit le noir',
  };

  // Une courbe animée : son repos, sa position affichée, l'écart de chaque
  // point à son repos et sa vitesse, la vitesse du repos pendant un trajet.
  function curveState(c) {
    return {
      rest: c, pos: Float32Array.from(c),
      D: new Float32Array(2 * N), V: new Float32Array(2 * N), RV: new Float32Array(2 * N),
    };
  }

  class Plate {
    constructor(img, opts = {}) {
      this.img = img;
      this.seed = opts.seed ?? Math.floor(Math.random() * 1e6);
      this.count = opts.subjects ?? 3;
      this.corners = opts.corners ?? 3;
      this.detail = opts.detail ?? 0.03;
      this.rays = opts.rays ?? true;
      this.fill = opts.fill in FILLS ? opts.fill : 'screen';
      this.palette = opts.palette in PALETTES ? opts.palette : 'vive';
      this.onseed = opts.onseed;
      this.onready = opts.onready;

      const canvas = document.createElement('canvas');
      canvas.className = 'aplats-canvas';
      canvas.tabIndex = 0;
      canvas.setAttribute('role', 'img');
      canvas.setAttribute('aria-label', (img.alt ? img.alt + ' — ' : '') +
        'aplats animés : ils évitent le curseur, un clic en envoie un vers une autre zone');
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');
      img.insertAdjacentElement('afterend', canvas);

      this.cursor = null;
      this.shapes = [];
      canvas.addEventListener('pointermove', (e) => {
        if (e.pointerType === 'touch') return;
        this.cursor = this.toImage(e);
        wake(this);
      });
      canvas.addEventListener('pointerleave', () => { this.cursor = null; wake(this); });
      canvas.addEventListener('click', (e) => this.click(this.toImage(e)));
      canvas.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter' && e.key !== ' ') return;
        e.preventDefault();
        if (this.shapes.length) this.send(this.shapes[0], null);
      });
      new ResizeObserver(() => this.resize()).observe(canvas);
    }

    toImage(e) {
      const r = this.canvas.getBoundingClientRect();
      return [(e.clientX - r.left) / r.width * this.W, (e.clientY - r.top) / r.height * this.H];
    }

    resize() {
      const r = this.canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = Math.max(1, Math.round(r.width * dpr)), h = Math.max(1, Math.round(r.height * dpr));
      if (w !== this.canvas.width || h !== this.canvas.height) {
        this.canvas.width = w;
        this.canvas.height = h;
        if (this.small) this.draw();
      }
    }

    setFill(fill) {
      if (!(fill in FILLS)) return;
      this.fill = fill;
      if (this.small) this.draw();
    }

    // Change de palette sans bouger les formes : chacune garde son rang dans
    // un ordre tiré de la graine, donc deux formes voisines restent distinctes.
    setPalette(name) {
      if (!(name in PALETTES)) return;
      this.palette = name;
      this.shapes.forEach((s, i) => { s.color = this.colorFor(i); });
      if (this.small) this.draw();
    }

    colorFor(i) {
      const colors = random(this.seed + 1).shuffle(Object.values(PALETTES[this.palette]));
      return colors[i % colors.length];
    }

    analyse() {
      const t0 = performance.now();
      const img = this.img;
      this.W = img.naturalWidth;
      this.H = img.naturalHeight;
      this.d = Math.hypot(this.W, this.H);

      // Toute l'analyse se fait sur une copie de 256 px : c'est elle qui coûte.
      const k = Math.max(1, Math.max(this.W, this.H) / ANALYSIS_SIZE);
      const w = Math.round(this.W / k), h = Math.round(this.H / k);
      const c = document.createElement('canvas');
      c.width = w; c.height = h;
      const cx = c.getContext('2d', { willReadFrequently: true });
      cx.imageSmoothingQuality = 'high';
      cx.drawImage(img, 0, 0, w, h);
      const px = cx.getImageData(0, 0, w, h).data;
      const r = new Float32Array(w * h), g = new Float32Array(w * h), b = new Float32Array(w * h), lum = new Float32Array(w * h);
      for (let i = 0; i < w * h; i++) {
        r[i] = px[4 * i] / 255; g[i] = px[4 * i + 1] / 255; b[i] = px[4 * i + 2] / 255;
        lum[i] = 0.299 * r[i] + 0.587 * g[i] + 0.114 * b[i];
      }
      this.small = { w, h, r, g, b, lum };
      this.k = this.W / w;
      this.ds = Math.hypot(w, h);
      // Gardées pour qui veut regarder l'analyse.
      this.saliency = saliency(this.small);
      this.zones = subjects(this.small, ZONES, this.saliency).map((p) => ({ mask: p.mask, score: p.score }));
      this.build();
      this.resize();
      this.draw();
      wake(this);
      this.ms = performance.now() - t0;
      if (this.onready) this.onready(this);
    }

    zoneBold(z) {
      const { w, h } = this.small;
      if (!z.bold) z.bold = boldShape(z.mask, w, h, this.ds);
      return z.bold;
    }

    // Une silhouette posée sur une zone : courbe élargie (décalée comme un
    // repérage raté), courbe du sujet (le trou du halo), clarté du fond.
    shapeOn(zi, main, rnd) {
      const z = this.zones[zi];
      const { w, h, lum } = this.small;
      const bold = this.zoneBold(z);
      const pad = this.ds * (main ? 0.025 : 0.015);
      const grown = dilate(bold, w, h, pad);
      const tol = this.detail * this.ds;
      let outer = curveOf(grown, w, h, this.k, tol);
      if (!outer) return null;
      const off = 0.012 * this.d;
      outer = translated(outer, rnd.uniform(-off, off), rnd.uniform(-off, off));
      const core = curveOf(bold, w, h, this.k, tol) || collapsed(outer);

      // Fond sombre : la couronne autour du sujet, comme pop.blend_for.
      let sum = 0, cnt = 0;
      for (let i = 0; i < grown.length; i++) if (grown[i] && !bold[i]) { sum += lum[i]; cnt++; }
      const dark = cnt && sum / cnt <= 0.5 ? 1 : 0;
      return { outer, core, dark, zone: zi };
    }

    build() {
      const rnd = random(this.seed);
      this.rnd = rnd;
      const stroke = 0.009 * this.d;
      this.stroke = stroke;
      this.vib = {
        gap: 0.018 * this.d, length: 0.035 * this.d, width: stroke * 0.85,
        spacing: 0.07 * this.d, arc: 0.06 * this.d, corners: this.corners,
        step: Math.max(1, stroke * 0.85 / 2),
        offset: rnd(), rand: Array.from({ length: 64 }, () => rnd()),
      };
      this.shapes = [];
      for (let zi = 0; zi < Math.min(this.count, this.zones.length); zi++) {
        const s = this.shapeOn(zi, this.shapes.length === 0, rnd);
        if (!s) continue;
        const shape = {
          color: this.colorFor(this.shapes.length),
          main: this.shapes.length === 0,
          zone: zi,
          dark: s.dark,
          outer: curveState(s.outer),
          core: curveState(align(s.outer, s.core)),
          T: [0, 0], TV: [0, 0],
          morph: null,
        };
        shape.corners = pickCorners(shape.outer.rest, this.vib);
        this.shapes.push(shape);
      }
    }

    reseed(seed) {
      this.seed = seed ?? Math.floor(Math.random() * 1e6);
      if (!this.small) return;
      this.build();
      this.draw();
      if (this.onseed) this.onseed(this.seed);
    }

    // Clic : sur une forme, elle part vers une autre zone saillante ; à côté,
    // la forme la plus proche vient à l'endroit cliqué.
    click(P) {
      if (!this.shapes.length) return;
      let mover = null;
      for (let i = this.shapes.length - 1; i >= 0; i--) {
        if (inside(this.shapes[i].outer.pos, P[0], P[1])) { mover = this.shapes[i]; break; }
      }
      if (mover) return this.send(mover, null);
      let best = Infinity;
      for (const s of this.shapes) {
        const [x, y] = centroid(s.outer.pos);
        const dd = Math.hypot(x - P[0], y - P[1]);
        if (dd < best) { best = dd; mover = s; }
      }
      this.send(mover, P);
    }

    send(shape, P) {
      const taken = new Set(this.shapes.filter((s) => s !== shape).map((s) => s.zone));
      const free = this.zones.map((_, i) => i).filter((i) => !taken.has(i) && i !== shape.zone);
      let zi = -1;
      if (P) {
        const { w, h } = this.small;
        const x = Math.min(w - 1, Math.floor(P[0] / this.k)), y = Math.min(h - 1, Math.floor(P[1] / this.k));
        zi = free.find((i) => this.zoneBold(this.zones[i])[y * w + x]) ?? -1;
      } else if (free.length) {
        zi = free[Math.floor(this.rnd() * free.length)];
      }
      let target = zi >= 0 ? this.shapeOn(zi, shape.main, this.rnd) : null;
      if (!target) {
        // Pas de zone libre : la forme glisse telle quelle, vers le clic ou au hasard.
        const [cx, cy] = centroid(shape.outer.rest);
        const to = P || [this.W * this.rnd.uniform(0.25, 0.75), this.H * this.rnd.uniform(0.25, 0.75)];
        target = {
          outer: translated(shape.outer.rest, to[0] - cx, to[1] - cy),
          core: translated(shape.core.rest, to[0] - cx, to[1] - cy),
          dark: shape.dark, zone: -1,
        };
      }
      shape.morph = {
        t: 0,
        outer: { from: Float32Array.from(shape.outer.rest), to: align(shape.outer.rest, target.outer) },
        core: { from: Float32Array.from(shape.core.rest), to: align(shape.core.rest, target.core) },
        fromDark: shape.dark, toDark: target.dark,
      };
      shape.zone = target.zone;
      if (reduceMotion) shape.morph.t = 1;
      wake(this);
    }

    // Un pas de simulation ; renvoie false quand tout est au repos.
    step(dt) {
      if (!this.small) return false;
      const d = this.d;
      let busy = !!this.cursor;
      const sub = 2, h = dt / sub;
      for (const s of this.shapes) {
        if (s.morph) {
          busy = true;
          const m = s.morph;
          m.t = Math.min(1, m.t + dt / TRAVEL);
          const e = m.t < 0.5 ? 4 * m.t ** 3 : 1 - (-2 * m.t + 2) ** 3 / 2;
          for (const key of ['outer', 'core']) {
            const c = s[key], { from, to } = m[key];
            for (let i = 0; i < 2 * N; i++) {
              const next = from[i] + (to[i] - from[i]) * e;
              const vel = dt > 0 ? (next - c.rest[i]) / dt : 0;
              // Pseudo-force d'inertie : la forme traîne puis rebondit à l'arrivée.
              if (!reduceMotion && dt > 0) c.V[i] -= INERTIA * (vel - c.RV[i]);
              c.RV[i] = vel;
              c.rest[i] = next;
            }
          }
          s.dark = m.fromDark + (m.toDark - m.fromDark) * e;
          if (m.t >= 1) {
            s.morph = null;
            s.outer.RV.fill(0); s.core.RV.fill(0);
            s.corners = pickCorners(s.outer.rest, this.vib);
          }
        }

        // Toute la forme glisse un peu pour s'écarter du curseur.
        const rest = s.outer.rest;
        const [cx, cy] = centroid(rest);
        let fx = 0, fy = 0;
        if (this.cursor && !reduceMotion) {
          let radius = 0;
          for (let i = 0; i < N; i++) radius = Math.max(radius, Math.hypot(rest[2 * i] - cx, rest[2 * i + 1] - cy));
          const ux = cx + s.T[0] - this.cursor[0], uy = cy + s.T[1] - this.cursor[1];
          const dist = Math.hypot(ux, uy), reach = radius + REACH * d;
          if (dist < reach) {
            const f = K * DRIFT * d * (1 - dist / reach) * Math.min(1, dist / (0.05 * d)) / Math.max(dist, 1e-3);
            fx = ux * f; fy = uy * f;
          }
        }
        for (let k = 0; k < sub; k++) {
          for (let a = 0; a < 2; a++) {
            s.TV[a] += h * ((a ? fy : fx) - K * 0.6 * s.T[a] - DAMP * s.TV[a]);
            s.T[a] += h * s.TV[a];
          }
          this.relax(s.outer, s.T, h);
          this.relax(s.core, s.T, h);
        }
        let motion = Math.hypot(s.T[0], s.T[1]) + Math.hypot(s.TV[0], s.TV[1]) * 0.05;
        for (const c of [s.outer, s.core]) {
          for (let i = 0; i < 2 * N; i++) {
            c.pos[i] = c.rest[i] + s.T[i & 1] + c.D[i];
            motion = Math.max(motion, Math.abs(c.D[i]) + Math.abs(c.V[i]) * 0.05);
          }
        }
        if (motion > 0.002 * d) busy = true;
      }
      this.draw();
      return busy;
    }

    // Chaque point est tiré vers son repos, lié à ses voisins, repoussé par
    // le curseur.
    relax(c, T, h) {
      const { D, V, rest } = c;
      const q = this.cursor && !reduceMotion ? this.cursor : null;
      const reach = REACH * this.d, push = K * PUSH * this.d;
      for (let i = 0; i < N; i++) {
        const p = (i - 1 + N) % N, n = (i + 1) % N;
        for (let a = 0; a < 2; a++) {
          const j = 2 * i + a;
          let f = -K * D[j] - DAMP * V[j] + NEIGHBOUR * (D[2 * p + a] + D[2 * n + a] - 2 * D[j]);
          if (q) {
            const ux = rest[2 * i] + T[0] + D[2 * i] - q[0];
            const uy = rest[2 * i + 1] + T[1] + D[2 * i + 1] - q[1];
            const dist = Math.hypot(ux, uy);
            if (dist < reach) f += push * (1 - dist / reach) ** 2 * (a ? uy : ux) / Math.max(dist, 1);
          }
          V[j] += h * f;
        }
      }
      for (let j = 0; j < 2 * N; j++) D[j] += h * V[j];
    }

    path(c, ctx) {
      // Une courbe quadratique par les milieux : lisse même agrandie.
      const n = c.length / 2;
      const mx = (i) => (c[2 * (i % n)] + c[2 * ((i + 1) % n)]) / 2;
      const my = (i) => (c[2 * (i % n) + 1] + c[2 * ((i + 1) % n) + 1]) / 2;
      ctx.moveTo(mx(0), my(0));
      for (let i = 1; i <= n; i++) ctx.quadraticCurveTo(c[2 * (i % n)], c[2 * (i % n) + 1], mx(i), my(i));
      ctx.closePath();
    }

    // Pose la couleur d'une forme d'une des façons de FILLS, avec un poids
    // pour fondre deux façons quand la forme passe d'un fond à l'autre.
    paint(s, how, weight) {
      if (weight < 0.001) return;
      const ctx = this.ctx, outer = s.outer.pos;
      ctx.save();
      ctx.fillStyle = s.color;
      ctx.strokeStyle = s.color;
      if (how === 'multiply' || how === 'screen') {
        ctx.globalCompositeOperation = how;
        ctx.globalAlpha = 0.95 * weight;
        ctx.beginPath(); this.path(outer, ctx); ctx.fill();
      } else if (how === 'halo') {
        // Le sujet reste la photo : on peint la forme moins sa silhouette.
        ctx.globalAlpha = 0.88 * weight;
        ctx.beginPath(); this.path(outer, ctx); ctx.clip();
        ctx.beginPath(); this.path(outer, ctx); this.path(s.core.pos, ctx); ctx.fill('evenodd');
      } else if (how === 'transparence') {
        ctx.globalAlpha = 0.5 * weight;
        ctx.beginPath(); this.path(outer, ctx); ctx.fill();
      } else if (how === 'trame') {
        // Hachures à 45° : couleur pleine, photo intacte entre les traits.
        ctx.globalAlpha = weight;
        ctx.beginPath(); this.path(outer, ctx); ctx.clip();
        let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
        for (let i = 0; i < N; i++) {
          x0 = Math.min(x0, outer[2 * i]); x1 = Math.max(x1, outer[2 * i]);
          y0 = Math.min(y0, outer[2 * i + 1]); y1 = Math.max(y1, outer[2 * i + 1]);
        }
        ctx.lineWidth = this.stroke * 0.8;
        ctx.beginPath();
        for (let t = x0 + y0; t < x1 + y1; t += this.stroke * 1.9) {
          ctx.moveTo(t - y0, y0);
          ctx.lineTo(t - y1, y1);
        }
        ctx.stroke();
      }
      ctx.restore();
    }

    draw() {
      const ctx = this.ctx, cw = this.canvas.width, ch = this.canvas.height;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(this.img, 0, 0, cw, ch);
      const sc = cw / this.W;
      ctx.setTransform(sc, 0, 0, ch / this.H, 0, 0);

      for (const s of this.shapes) {
        if (this.fill === 'figures') {
          this.paint(s, 'multiply', 1 - s.dark);
          this.paint(s, 'halo', s.dark);
        } else if (this.fill === 'screen') {
          this.paint(s, 'multiply', 1 - s.dark);
          this.paint(s, 'screen', s.dark);
        } else {
          this.paint(s, this.fill, 1);
        }
      }

      ctx.strokeStyle = CONTOUR;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.lineWidth = this.stroke;
      for (const s of this.shapes) { ctx.beginPath(); this.path(s.outer.pos, ctx); ctx.stroke(); }

      const main = this.shapes.find((s) => s.main);
      if (main && this.rays) {
        ctx.lineWidth = this.vib.width;
        ctx.beginPath();
        for (const line of vibrationLines(main.outer.pos, this.vib, main.corners)) {
          ctx.moveTo(line[0][0], line[0][1]);
          for (let i = 1; i < line.length; i++) ctx.lineTo(line[i][0], line[i][1]);
        }
        ctx.stroke();
      }
    }
  }

  // ------------------------------------------------------------------------
  // Mise en route
  // ------------------------------------------------------------------------

  // Les analyses passent une à une, quand l'image approche de l'écran.
  const queue = [];
  let running = false;
  function enqueue(plate) {
    queue.push(plate);
    if (running) return;
    running = true;
    const next = () => {
      const p = queue.shift();
      if (!p) { running = false; return; }
      try {
        p.analyse();
        p.canvas.classList.add('is-ready');
      } catch (err) {
        console.warn('aplats : analyse impossible', p.img.currentSrc, err);
        p.canvas.remove();
      }
      setTimeout(next, 0);
    };
    setTimeout(next, 0);
  }

  const seen = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      seen.unobserve(e.target);
      enqueue(e.target.__aplats);
    }
  }, { rootMargin: '300px' });

  function attach(img, opts = {}) {
    if (img.__aplats) return img.__aplats;
    const plate = new Plate(img, opts);
    img.__aplats = plate;
    const go = () => {
      if (opts.eager) enqueue(plate);
      else seen.observe(img);
    };
    if (img.complete && img.naturalWidth) go();
    else img.addEventListener('load', go, { once: true });
    return plate;
  }

  function auto() {
    document.querySelectorAll('img[data-aplats]').forEach((img) => {
      const seed = img.dataset.seed ? Number(img.dataset.seed) : undefined;
      attach(img, { seed, fill: img.dataset.fill, palette: img.dataset.palette });
    });
  }

  window.Aplats = { attach, fills: FILLS, palettes: PALETTES, FOND, CONTOUR };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', auto);
  else auto();
})();

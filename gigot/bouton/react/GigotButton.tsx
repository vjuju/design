'use client';

/**
 * GigotButton — le pictogramme gigot sous forme de bouton-case à cocher.
 *
 * Survol (non coché) : la face du O suit le curseur, les arcs pivotent à 90° de l'axe centre → curseur.
 *                      Les deux gardent leur position quand le curseur quitte le carré.
 * Clic (coché)       : la face rejoint le flanc, un seul rond recentré rebondit légèrement,
 *                      les arcs s'allongent et s'aplatissent en paupières depuis leur angle courant,
 *                      des petits traits rayonnent dans le O ; la pupille et les traits suivent le curseur.
 * Re-clic            : tout revient, les arcs retrouvent l'angle qu'ils avaient au moment du clic.
 *
 * Contrôlé (`checked` + `onCheckedChange`) ou non contrôlé (`defaultChecked`).
 */

import { useCallback, useEffect, useRef, useState, type CSSProperties, type PointerEvent } from 'react';
import styles from './GigotButton.module.css';

export const GIGOT_COULEURS = {
  noir: '#111111',
  blanc: '#FFFFFF',
  rose: '#FF3EA5',
  jaune: '#FFD60A',
  violet: '#7B2FF7',
  cyan: '#2EC4F1',
  vert: '#39D353',
  orange: '#FF6A13',
} as const;
export type GigotCouleur = keyof typeof GIGOT_COULEURS;

/** Encre (arcs) blanche seulement sur les fonds sombres — contraste ≥ 4,5:1. */
const encrePour = (fond: GigotCouleur) =>
  fond === 'noir' || fond === 'violet' ? GIGOT_COULEURS.blanc : GIGOT_COULEURS.noir;

type Props = {
  fond?: GigotCouleur;
  face?: GigotCouleur;
  flanc?: GigotCouleur;
  /** côté du carré en px (défaut 132) */
  taille?: number;
  checked?: boolean;
  defaultChecked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  /** nom accessible du bouton */
  label?: string;
  className?: string;
};

// ---- géométrie (repère 160 × 160) ----
const ARC_ANGLE = 225;                         // milieu de l'arc 1 au repos (haut gauche)
const OEIL_R = 76.9, OEIL_DEMI = 48, OEIL_HAUT = 18; // paupières : plus plates qu'un cercle
const DUREE = 600;                             // ms, transition arcs ↔ paupières

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const proche = (angle: number, ref: number) => ref + ((((angle - ref) % 360) + 540) % 360 - 180);
function tourne(x: number, y: number, deg: number): [number, number] {
  const a = (deg * Math.PI) / 180, dx = x - 80, dy = y - 80;
  return [80 + dx * Math.cos(a) - dy * Math.sin(a), 80 + dx * Math.sin(a) + dy * Math.cos(a)];
}
function arc(cx: number, cy: number, R: number, milieu: number, demi: number) {
  const a = ((milieu - demi) * Math.PI) / 180, b = ((milieu + demi) * Math.PI) / 180;
  const f = (n: number) => n.toFixed(1);
  return `M${f(cx + R * Math.cos(a))} ${f(cy + R * Math.sin(a))}A${f(R)} ${f(R)} 0 0 1 ${f(cx + R * Math.cos(b))} ${f(cy + R * Math.sin(b))}`;
}
const ARC1_REPOS = arc(73, 73, 60, 225, 25);
const ARC2_REPOS = arc(87, 87, 60, 45, 25);

export default function GigotButton({
  fond = 'rose',
  face = 'cyan',
  flanc = 'violet',
  taille = 132,
  checked,
  defaultChecked = false,
  onCheckedChange,
  label = 'gigot',
  className,
}: Props) {
  const [interne, setInterne] = useState(defaultChecked);
  const coche = checked ?? interne;

  const btn = useRef<HTMLButtonElement>(null);
  const arc1 = useRef<SVGPathElement>(null);
  const arc2 = useRef<SVGPathElement>(null);
  const etat = useRef({ rot: 0, rotC: 0, t: defaultChecked ? 1 : 0, raf: 0, premier: true, reduit: false });

  const setVar = (nom: string, valeur: string) => btn.current?.style.setProperty(nom, valeur);

  const tourneVers = useCallback((cible: number) => {
    const e = etat.current;
    e.rot += ((((cible - e.rot) % 360) + 540) % 360) - 180; // chemin le plus court
    setVar('--rot', `${e.rot.toFixed(1)}deg`);
  }, []);

  const dessine = useCallback((t: number) => {
    const { rotC } = etat.current;
    const R = lerp(60, OEIL_R, t), demi = lerp(25, OEIL_DEMI, t);
    const haut = tourne(80, OEIL_HAUT + OEIL_R, -rotC);
    const bas = tourne(80, 160 - OEIL_HAUT - OEIL_R, -rotC);
    // chaque arc rejoint la paupière la plus proche pour tourner le moins possible
    const a1 = proche(270 - rotC, 225), b1 = proche(90 - rotC, 225);
    const versHaut = Math.abs(a1 - 225) <= Math.abs(b1 - 225);
    const p1 = versHaut ? haut : bas, p2 = versHaut ? bas : haut;
    const m1 = versHaut ? a1 : b1, m2 = proche(m1 - 180, 45);
    arc1.current?.setAttribute('d', arc(lerp(73, p1[0], t), lerp(73, p1[1], t), R, lerp(225, m1, t), demi));
    arc2.current?.setAttribute('d', arc(lerp(87, p2[0], t), lerp(87, p2[1], t), R, lerp(45, m2, t), demi));
  }, []);

  // préférences de mouvement + état initial
  useEffect(() => {
    etat.current.reduit = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    dessine(etat.current.t);
    return () => cancelAnimationFrame(etat.current.raf);
  }, [dessine]);

  // animation arcs ↔ paupières à chaque changement d'état
  useEffect(() => {
    const e = etat.current;
    if (e.premier) { e.premier = false; return; }
    if (coche) e.rotC = e.rot; // l'œil se forme depuis l'orientation courante des arcs
    else { setVar('--px', '0px'); setVar('--py', '0px'); }
    cancelAnimationFrame(e.raf);
    const vers = coche ? 1 : 0;
    if (e.reduit) { e.t = vers; dessine(vers); return; }
    const depart = e.t;
    let t0: number | null = null;
    const pas = (ts: number) => {
      if (t0 === null) t0 = ts;
      const k = Math.min(1, (ts - t0) / DUREE);
      const ease = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      e.t = depart + (vers - depart) * ease;
      dessine(e.t);
      if (k < 1) e.raf = requestAnimationFrame(pas);
    };
    e.raf = requestAnimationFrame(pas);
  }, [coche, dessine]);

  const onPointerMove = (ev: PointerEvent<HTMLButtonElement>) => {
    if (etat.current.reduit || !btn.current) return;
    const r = btn.current.getBoundingClientRect();
    const dx = (ev.clientX - r.left) / r.width - 0.5; // -0,5 → 0,5
    const dy = (ev.clientY - r.top) / r.height - 0.5;
    if (coche) { // l'œil regarde le curseur
      setVar('--px', `${(dx * 20).toFixed(1)}px`);
      setVar('--py', `${(dy * 20).toFixed(1)}px`);
      return;
    }
    setVar('--fx', `${(dx * 16).toFixed(1)}px`);
    setVar('--fy', `${(dy * 16).toFixed(1)}px`);
    if (Math.abs(dx) + Math.abs(dy) > 0.04) {
      const phi = (Math.atan2(dy, dx) * 180) / Math.PI;
      tourneVers(phi + 90 - ARC_ANGLE); // arcs perpendiculaires à l'axe centre → curseur
    }
  };

  const onClick = () => {
    const suivant = !coche;
    if (checked === undefined) setInterne(suivant);
    onCheckedChange?.(suivant);
  };

  const encre = encrePour(fond);
  const C = GIGOT_COULEURS;

  return (
    <button
      ref={btn}
      type="button"
      aria-pressed={coche}
      aria-label={label}
      onClick={onClick}
      onPointerMove={onPointerMove}
      className={[styles.btn, coche && styles.coche, className].filter(Boolean).join(' ')}
      style={{ '--taille': `${taille}px` } as CSSProperties}
    >
      <svg viewBox="0 0 160 160" aria-hidden="true">
        <rect width="160" height="160" fill={C[fond]} />
        <g className={styles.arcs} fill="none" stroke={encre} strokeWidth={7} strokeLinecap="round">
          <path ref={arc1} d={ARC1_REPOS} />
          <path ref={arc2} d={ARC2_REPOS} />
        </g>
        <g className={styles.iris}>
          <circle className={styles.flanc} cx={87} cy={87} r={46} fill={C[flanc]} stroke="#111111" strokeWidth={7} />
          <g className={styles.face}>
            <circle cx={73} cy={73} r={46} fill={C[face]} stroke="#111111" strokeWidth={7} />
            <circle className={styles.pupille} cx={73} cy={73} r={13} fill="#111111" />
          </g>
          <g className={styles.pupille} stroke="#111111" strokeWidth={4} strokeLinecap="round">
            {Array.from({ length: 8 }, (_, i) => (
              <line
                key={i}
                className={styles.rayon}
                style={{ '--a': `${i * 45 + 22.5}deg` } as CSSProperties}
                x1={101} y1={80} x2={108} y2={80}
              />
            ))}
          </g>
        </g>
      </svg>
    </button>
  );
}

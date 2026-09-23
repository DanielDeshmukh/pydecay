/** Pure decay math and display formatting used by the landing page playground and hero plot. */

export const CHART = {
  left: 62,
  right: 712,
  top: 58,
  bottom: 330,
  width: 650,
  maxHalfLives: 5,
  /** Vertical span of the decay marker circle path (bottom − top − padding). */
  markerSpan: 272,
} as const;

/**
 * SVG path for an exponential decay curve over `halfLives` half-lives.
 * Sampled at 101 points; y follows A(t)/A0 = 2^(−progress · halfLives).
 */
export function decayPath(
  x: number,
  top: number,
  bottom: number,
  width: number,
  halfLives: number,
): string {
  return Array.from({ length: 101 }, (_, index) => {
    const progress = index / 100;
    const px = x + width * progress;
    const py = bottom - (bottom - top) * Math.pow(0.5, halfLives * progress);
    return `${index === 0 ? "M" : "L"}${px.toFixed(2)} ${py.toFixed(2)}`;
  }).join(" ");
}

/** Fraction of activity remaining after `halfLives` half-lives: 0.5^n. */
export function remainingFraction(halfLives: number): number {
  return Math.pow(0.5, halfLives);
}

/** Activity remaining after `halfLives` half-lives: A0 · 0.5^n. */
export function decayedActivity(initialActivity: number, halfLives: number): number {
  return initialActivity * remainingFraction(halfLives);
}

/**
 * Elapsed calendar time for `halfLives` half-lives, expressed in
 * `daysPerUnit` (1 = days, 365.2422 = years, 1/24 = hours).
 */
export function elapsedTime(halfLives: number, halfLifeDays: number, daysPerUnit: number): number {
  return (halfLives * halfLifeDays) / daysPerUnit;
}

/** Parse the playground activity input; fall back to 1000 Bq when invalid. */
export function parseActivityInput(raw: string): number {
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1000;
}

/** Literal for the generated Python snippet (prefer `N.0` for integers). */
export function activityLiteral(value: number): string {
  return Number.isInteger(value) && !String(value).includes("e") ? `${value}.0` : String(value);
}

/** Marker x on the 0–5 half-life axis. */
export function markerX(halfLives: number): number {
  return CHART.left + (CHART.width * halfLives) / CHART.maxHalfLives;
}

/** Marker y on the activity axis for the remaining fraction. */
export function markerY(remaining: number): number {
  return CHART.bottom - CHART.markerSpan * remaining;
}

/** Percentage string for the playground readout (two decimal places). */
export function percentRemaining(remaining: number): string {
  return (remaining * 100).toFixed(2);
}

/** Locale activity display: more precision for small values. */
export function formatActivity(value: number): string {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: value >= 10 ? 2 : value >= 1 ? 3 : 6,
    minimumFractionDigits: value >= 10 ? 2 : 0,
  }).format(value);
}

/** Activity-axis tick label (0, 1.5, 12, 1.2k, 2k, …). */
export function formatAxis(value: number): string {
  if (value === 0) return "0";
  if (value >= 1000) return `${(value / 1000).toFixed(value % 1000 === 0 ? 0 : 1)}k`;
  if (value >= 10) return String(Math.round(value));
  return value.toFixed(value >= 1 ? 1 : 2);
}

/** Time-axis tick label. */
export function formatTimeTick(value: number): string {
  if (value === 0) return "0";
  if (value >= 10) return String(Math.round(value));
  return value.toFixed(1);
}

/** Exact curie definition: 1 Ci = 3.7e10 Bq (NIST SP 811). Matches pydecay.units.CI_IN_BQ. */
export const CI_IN_BQ = 3.7e10;

/** Avogadro constant 1/mol (exact, 2019 SI). Matches pydecay.units.AVOGADRO_PER_MOL. */
export const AVOGADRO_PER_MOL = 6.02214076e23;

/** Becquerels → curies (pydecay.bq_to_ci). */
export function bqToCi(bq: number): number {
  return bq / CI_IN_BQ;
}

/** Curies → becquerels (pydecay.ci_to_bq). */
export function ciToBq(ci: number): number {
  return ci * CI_IN_BQ;
}

/** Atom count → grams via atomic mass in u (pydecay.atoms_to_grams). */
export function atomsToGrams(nAtoms: number, atomicMassU: number): number {
  return (nAtoms * atomicMassU) / AVOGADRO_PER_MOL;
}

/** Grams → atom count via atomic mass in u (pydecay.grams_to_atoms). */
export function gramsToAtoms(mG: number, atomicMassU: number): number {
  return (mG * AVOGADRO_PER_MOL) / atomicMassU;
}

/** λ = ln(2) / T½ for a half-life in seconds (pydecay.decay_constant). */
export function decayConstant(halfLifeS: number): number {
  return Math.LN2 / halfLifeS;
}

/** τ = 1 / λ mean lifetime in seconds (pydecay.mean_lifetime_s). */
export function meanLifetimeS(lambda: number): number {
  return 1 / lambda;
}

/** Multipliers to seconds for to_seconds-style parsing (aligns with common pint spellings). */
const TIME_UNIT_SECONDS: Record<string, number> = {
  s: 1,
  sec: 1,
  secs: 1,
  second: 1,
  seconds: 1,
  min: 60,
  mins: 60,
  minute: 60,
  minutes: 60,
  h: 3600,
  hr: 3600,
  hrs: 3600,
  hour: 3600,
  hours: 3600,
  d: 86400,
  day: 86400,
  days: 86400,
  week: 604800,
  weeks: 604800,
  year: 31557600,
  years: 31557600,
  y: 31557600,
  yr: 31557600,
  yrs: 31557600,
};

/**
 * Parse a time into seconds (pydecay.to_seconds).
 * Plain non-negative finite numbers pass through; strings like "8.02 days"
 * are multiplied by the unit factor. Invalid input throws.
 */
export function toSeconds(value: number | string): number {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error(`time must be finite, got ${value}`);
    if (value < 0) throw new Error(`time must be >= 0, got ${value}`);
    return value;
  }
  const match = value.trim().match(/^(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([a-zA-Z]+)$/);
  if (!match) throw new Error(`cannot parse time from ${JSON.stringify(value)}`);
  const amount = Number(match[1]);
  const unit = match[2].toLowerCase();
  const factor = TIME_UNIT_SECONDS[unit];
  if (factor === undefined) throw new Error(`unknown time unit ${match[2]}`);
  const seconds = amount * factor;
  if (seconds < 0) throw new Error(`time must be >= 0, got ${seconds}`);
  return seconds;
}

/** Locale-friendly number for converter readouts (scientific for extremes). */
export function formatConverter(value: number): string {
  if (!Number.isFinite(value)) return String(value);
  if (value === 0) return "0";
  const abs = Math.abs(value);
  if (abs >= 1e-6 && abs < 1e15) {
    return new Intl.NumberFormat("en-US", { maximumSignificantDigits: 12 }).format(value);
  }
  return value
    .toExponential(6)
    .replace(/(\.\d*?)0+e/, "$1e")
    .replace(/\.e/, "e");
}

/** Factor description for the unit converter (e.g. "1 Ci = 3.7 × 10¹⁰ Bq"). */
export const UNIT_FACTS = {
  ciInBq: "1 Ci = 3.7 × 10¹⁰ Bq",
  avogadro: "1 mol = 6.02214076 × 10²³ atoms",
  ln2: "λ = ln(2) / t½   ·   τ = 1 / λ",
} as const;

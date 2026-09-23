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

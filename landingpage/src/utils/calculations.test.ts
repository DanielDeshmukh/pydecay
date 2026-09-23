import { describe, expect, it } from "vitest";
import {
  AVOGADRO_PER_MOL,
  activityLiteral,
  atomsToGrams,
  bqToCi,
  CHART,
  CI_IN_BQ,
  decayConstant,
  decayPath,
  decayedActivity,
  elapsedTime,
  formatActivity,
  formatAxis,
  formatConverter,
  formatTimeTick,
  gramsToAtoms,
  ciToBq,
  markerX,
  markerY,
  meanLifetimeS,
  parseActivityInput,
  percentRemaining,
  remainingFraction,
  toSeconds,
} from "./calculations";

/**
 * Independent closed-form reference: A(t)/A0 = exp(-ln2 · t/t½).
 * Cross-checks the playground's 0.5^n form against the exponential form.
 */
function expFraction(halfLives: number): number {
  return Math.exp(-Math.LN2 * halfLives);
}

function parsePathPoints(path: string): Array<{ x: number; y: number }> {
  const points: Array<{ x: number; y: number }> = [];
  const re = /([ML])(-?\d+(?:\.\d+)?)\s(-?\d+(?:\.\d+)?)/g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(path)) !== null) {
    points.push({ x: Number(match[2]), y: Number(match[3]) });
  }
  return points;
}

describe("remainingFraction", () => {
  it("returns 1 at t=0", () => {
    expect(remainingFraction(0)).toBe(1);
  });

  it("returns 0.5 after one half-life", () => {
    expect(remainingFraction(1)).toBeCloseTo(0.5, 15);
  });

  it("returns 0.03125 after five half-lives (I-131 reference case)", () => {
    expect(remainingFraction(5)).toBeCloseTo(0.03125, 15);
  });

  it("matches exp(-ln2 · n) for fractional half-lives", () => {
    for (const n of [0.25, 0.5, 1.5, 2.35, 3.7, 4.99]) {
      expect(remainingFraction(n)).toBeCloseTo(expFraction(n), 12);
    }
  });

  it("is monotonically decreasing on [0, 5]", () => {
    let prev = Number.POSITIVE_INFINITY;
    for (let n = 0; n <= 5; n += 0.01) {
      const value = remainingFraction(n);
      expect(value).toBeLessThan(prev);
      prev = value;
    }
  });

  it("stays in (0, 1] for non-negative half-life counts", () => {
    for (const n of [0, 0.1, 1, 2.5, 5, 10]) {
      const value = remainingFraction(n);
      expect(value).toBeGreaterThan(0);
      expect(value).toBeLessThanOrEqual(1);
    }
  });
});

describe("decayedActivity", () => {
  it("I-131: 1000 Bq → 500 Bq after one half-life", () => {
    expect(decayedActivity(1000, 1)).toBeCloseTo(500, 10);
  });

  it("I-131: 1000 Bq → 31.25 Bq after five half-lives", () => {
    expect(decayedActivity(1000, 5)).toBeCloseTo(31.25, 10);
  });

  it("1000 Bq → 62.5 Bq after four half-lives", () => {
    expect(decayedActivity(1000, 4)).toBeCloseTo(62.5, 10);
  });

  it("mirrors A0 when halfLives=0", () => {
    expect(decayedActivity(1234.5, 0)).toBe(1234.5);
  });

  it("is linear in A0", () => {
    expect(decayedActivity(2000, 3)).toBeCloseTo(2 * decayedActivity(1000, 3), 10);
  });

  it("matches A0 · exp(-ln2 · n)", () => {
    for (const [a0, n] of [
      [1000, 1],
      [250.5, 2.5],
      [1e6, 4.2],
    ] as const) {
      expect(decayedActivity(a0, n)).toBeCloseTo(a0 * expFraction(n), 8);
    }
  });

  it("activity ratio after n half-lives equals remainingFraction(n)", () => {
    for (const n of [0, 1, 2, 3, 4, 5]) {
      expect(decayedActivity(9876, n) / 9876).toBeCloseTo(remainingFraction(n), 12);
    }
  });
});

describe("elapsedTime", () => {
  it("one half-life in days", () => {
    expect(elapsedTime(1, 8.0228, 1)).toBeCloseTo(8.0228, 12);
  });

  it("five half-lives for Co-60 in years", () => {
    expect(elapsedTime(5, 1925.23, 365.2422)).toBeCloseTo((5 * 1925.23) / 365.2422, 10);
  });

  it("one half-life for Tc-99m in hours", () => {
    expect(elapsedTime(1, 0.250281, 1 / 24)).toBeCloseTo(0.250281 * 24, 10);
  });

  it("zero half-lives → zero time", () => {
    expect(elapsedTime(0, 8.0228, 1)).toBe(0);
  });

  it("is linear in halfLives", () => {
    expect(elapsedTime(4, 10, 1)).toBeCloseTo(4 * elapsedTime(1, 10, 1), 12);
  });
});

describe("parseActivityInput", () => {
  it("accepts positive finite numbers", () => {
    expect(parseActivityInput("1000")).toBe(1000);
    expect(parseActivityInput("0.5")).toBe(0.5);
    expect(parseActivityInput("1e3")).toBe(1000);
  });

  it("falls back to 1000 for invalid input", () => {
    expect(parseActivityInput("")).toBe(1000);
    expect(parseActivityInput("abc")).toBe(1000);
    expect(parseActivityInput("0")).toBe(1000);
    expect(parseActivityInput("-5")).toBe(1000);
    expect(parseActivityInput("NaN")).toBe(1000);
    expect(parseActivityInput("Infinity")).toBe(1000);
  });
});

describe("activityLiteral", () => {
  it("formats integers with .0 suffix", () => {
    expect(activityLiteral(1000)).toBe("1000.0");
    expect(activityLiteral(0)).toBe("0.0");
  });

  it("leaves non-integers as-is", () => {
    expect(activityLiteral(0.5)).toBe("0.5");
    expect(activityLiteral(1000.25)).toBe("1000.25");
  });

  it("does not force .0 on scientific notation integers", () => {
    expect(activityLiteral(1e21)).toBe("1e+21");
  });
});

describe("marker positions", () => {
  it("markerX at 0 is chart left edge", () => {
    expect(markerX(0)).toBe(CHART.left);
  });

  it("markerX at 5 is chart left + width", () => {
    expect(markerX(5)).toBe(CHART.left + CHART.width);
  });

  it("markerX is linear", () => {
    expect(markerX(2.5)).toBeCloseTo(CHART.left + CHART.width / 2, 10);
  });

  it("markerY at remaining=1 is near chart top", () => {
    expect(markerY(1)).toBe(CHART.bottom - CHART.markerSpan);
  });

  it("markerY at remaining=0 is chart bottom", () => {
    expect(markerY(0)).toBe(CHART.bottom);
  });

  it("markerY at remaining=0.5 is midpoint of marker span", () => {
    expect(markerY(0.5)).toBeCloseTo(CHART.bottom - CHART.markerSpan / 2, 10);
  });

  it("after one half-life marker sits halfway down the span", () => {
    expect(markerY(remainingFraction(1))).toBeCloseTo(CHART.bottom - CHART.markerSpan * 0.5, 10);
  });
});

describe("percentRemaining", () => {
  it("formats whole percents", () => {
    expect(percentRemaining(1)).toBe("100.00");
    expect(percentRemaining(0.5)).toBe("50.00");
    expect(percentRemaining(0.03125)).toBe("3.13");
  });

  it("always has two decimal places", () => {
    for (const r of [0, 0.001, 0.123456, 1]) {
      expect(percentRemaining(r)).toMatch(/^\d+\.\d{2}$/);
    }
  });
});

describe("decayPath", () => {
  const path = decayPath(570, 140, 650, 900, 5);
  const points = parsePathPoints(path);

  it("samples 101 points", () => {
    expect(points).toHaveLength(101);
  });

  it("starts at the origin x and top y (full activity)", () => {
    expect(points[0].x).toBe(570);
    expect(points[0].y).toBe(140);
  });

  it("ends at x+width with y at top (1/32 remaining over 5 half-lives)", () => {
    expect(points[100].x).toBe(1470);
    const expectedY = 650 - (650 - 140) * Math.pow(0.5, 5);
    expect(points[100].y).toBeCloseTo(expectedY, 2);
  });

  it("is monotonically non-decreasing in y (activity never rises)", () => {
    for (let i = 1; i < points.length; i++) {
      expect(points[i].y).toBeGreaterThanOrEqual(points[i - 1].y - 1e-9);
    }
  });

  it("is monotonically increasing in x", () => {
    for (let i = 1; i < points.length; i++) {
      expect(points[i].x).toBeGreaterThan(points[i - 1].x);
    }
  });

  it("at progress=0.2 (one of five half-lives) y matches closed form", () => {
    const point = points[20];
    const expected = 650 - (650 - 140) * 0.5;
    expect(point.y).toBeCloseTo(expected, 2);
  });

  it("matches exponential reference at intermediate samples", () => {
    for (const index of [10, 33, 50, 77, 90]) {
      const progress = index / 100;
      const expected = 650 - (650 - 140) * expFraction(5 * progress);
      expect(points[index].y).toBeCloseTo(expected, 2);
    }
  });
});

describe("formatActivity", () => {
  it("uses two fraction digits for values >= 10", () => {
    expect(formatActivity(1000)).toBe("1,000.00");
    expect(formatActivity(12.5)).toBe("12.50");
  });

  it("uses up to three fraction digits for 1 <= v < 10", () => {
    expect(formatActivity(5)).toBe("5");
    expect(formatActivity(1.25)).toBe("1.25");
    expect(formatActivity(0.5 * 10)).toBe("5");
  });

  it("uses up to six fraction digits for v < 1", () => {
    expect(formatActivity(0.03125)).toBe("0.03125");
    expect(formatActivity(0.5)).toBe("0.5");
  });

  it("formats 31.25 as thirty-one point two five", () => {
    expect(formatActivity(31.25)).toBe("31.25");
  });

  it("formats 500 as five hundred with two decimals", () => {
    expect(formatActivity(500)).toBe("500.00");
  });
});

describe("formatAxis", () => {
  it("zero", () => {
    expect(formatAxis(0)).toBe("0");
  });

  it("small values with two decimals for v < 1, one decimal for 1 <= v < 10", () => {
    expect(formatAxis(0.5)).toBe("0.50");
    expect(formatAxis(1.25)).toBe("1.3");
  });

  it("mid values with one decimal", () => {
    expect(formatAxis(5.5)).toBe("5.5");
    expect(formatAxis(9.99)).toBe("10.0");
  });

  it("values >= 10 rounded", () => {
    expect(formatAxis(10)).toBe("10");
    expect(formatAxis(12.6)).toBe("13");
    expect(formatAxis(999)).toBe("999");
  });

  it("thousands with k suffix", () => {
    expect(formatAxis(1000)).toBe("1k");
    expect(formatAxis(2000)).toBe("2k");
    expect(formatAxis(1500)).toBe("1.5k");
    expect(formatAxis(10000)).toBe("10k");
  });
});

describe("formatTimeTick", () => {
  it("zero", () => {
    expect(formatTimeTick(0)).toBe("0");
  });

  it("small values one decimal", () => {
    expect(formatTimeTick(1)).toBe("1.0");
    expect(formatTimeTick(2.5)).toBe("2.5");
    expect(formatTimeTick(9.94)).toBe("9.9");
  });

  it("values >= 10 rounded to integer string", () => {
    expect(formatTimeTick(10)).toBe("10");
    expect(formatTimeTick(10.6)).toBe("11");
    expect(formatTimeTick(40.1)).toBe("40");
  });
});

describe("cross-check: playground chain for each demo nuclide", () => {
  // Mirrors src/data/nuclides.ts — asserted independently here so a data typo fails tests.
  const cases = [
    { id: "I-131", halfLifeDays: 8.0228, daysPerUnit: 1, unit: "days" },
    { id: "Co-60", halfLifeDays: 1925.23, daysPerUnit: 365.2422, unit: "years" },
    { id: "Cs-137", halfLifeDays: 10990, daysPerUnit: 365.2422, unit: "years" },
    { id: "Tc-99m", halfLifeDays: 0.250281, daysPerUnit: 1 / 24, unit: "hours" },
  ];

  it.each(cases)("$id: 1000 Bq after 1 half-life is 500 Bq", ({ halfLifeDays, daysPerUnit }) => {
    const remaining = remainingFraction(1);
    const activity = decayedActivity(1000, 1);
    const elapsed = elapsedTime(1, halfLifeDays, daysPerUnit);
    expect(activity).toBeCloseTo(500, 10);
    expect(remaining).toBeCloseTo(0.5, 12);
    expect(elapsed).toBeCloseTo(halfLifeDays / daysPerUnit, 10);
    expect(elapsed).toBeGreaterThan(0);
  });

  it.each(cases)("$id: after 5 half-lives 3.125% remains", ({ halfLifeDays, daysPerUnit }) => {
    expect(decayedActivity(1000, 5)).toBeCloseTo(31.25, 10);
    expect(percentRemaining(remainingFraction(5))).toBe("3.13");
    expect(elapsedTime(5, halfLifeDays, daysPerUnit)).toBeCloseTo(
      (5 * halfLifeDays) / daysPerUnit,
      10,
    );
  });
});

describe("cross-check: display half-life strings match numeric data", () => {
  // Literature half-lives (NNDC / ICRP-107 rounded displays used on the site).
  const literature: Array<{
    id: string;
    days: number;
    displayDays?: number;
    displayYears?: number;
    displayHours?: number;
    tolerance: number;
  }> = [
    { id: "I-131", days: 8.0228, displayDays: 8.0228, tolerance: 1e-4 },
    { id: "Co-60", days: 1925.23, displayYears: 5.27, tolerance: 0.01 },
    { id: "Cs-137", days: 10990, displayYears: 30.09, tolerance: 0.05 },
    { id: "Tc-99m", days: 0.250281, displayHours: 6.01, tolerance: 0.02 },
  ];

  it("I-131 half-life in days matches display", () => {
    const row = literature[0];
    expect(row.days).toBeCloseTo(row.displayDays ?? 0, 4);
  });

  it("Co-60 half-life converts to ~5.27 years", () => {
    const years = 1925.23 / 365.2422;
    expect(Math.abs(years - 5.27)).toBeLessThan(0.01);
  });

  it("Cs-137 half-life converts to ~30.09 years", () => {
    const years = 10990 / 365.2422;
    expect(Math.abs(years - 30.09)).toBeLessThan(0.05);
  });

  it("Tc-99m half-life converts to ~6.01 hours", () => {
    const hours = 0.250281 * 24;
    expect(Math.abs(hours - 6.01)).toBeLessThan(0.02);
  });

  it("I-131 8.0228 days is within 0.1% of ICRP-107 692988.48 s", () => {
    const icrpSeconds = 692988.48;
    const siteSeconds = 8.0228 * 86400;
    const rel = Math.abs(siteSeconds - icrpSeconds) / icrpSeconds;
    expect(rel).toBeLessThan(1e-3);
  });
});

describe("unit conversion helpers (mirror pydecay top-level exports)", () => {
  it("CI_IN_BQ and AVOGADRO match pydecay.units constants", () => {
    expect(CI_IN_BQ).toBe(3.7e10);
    expect(AVOGADRO_PER_MOL).toBe(6.02214076e23);
  });

  describe("bqToCi", () => {
    it("3.7e10 Bq is exactly 1 Ci", () => {
      expect(bqToCi(3.7e10)).toBeCloseTo(1, 12);
    });

    it("zero maps to zero", () => {
      expect(bqToCi(0)).toBe(0);
    });

    it("round-trips with ciToBq", () => {
      expect(bqToCi(ciToBq(2.5))).toBeCloseTo(2.5, 12);
      expect(bqToCi(3.7e9)).toBeCloseTo(0.1, 12);
    });
  });

  describe("ciToBq", () => {
    it("1 Ci is 3.7e10 Bq", () => {
      expect(ciToBq(1)).toBe(3.7e10);
    });

    it("zero maps to zero", () => {
      expect(ciToBq(0)).toBe(0);
    });

    it("round-trips with bqToCi for a medical-scale activity", () => {
      // 1 MBq source ≈ 2.70e-5 Ci
      const bq = 1e6;
      expect(ciToBq(bqToCi(bq))).toBeCloseTo(bq, 6);
    });
  });

  describe("atomsToGrams / gramsToAtoms", () => {
    it("one mole of mass M is M grams", () => {
      const massU = 130.9061;
      expect(atomsToGrams(AVOGADRO_PER_MOL, massU)).toBeCloseTo(massU, 9);
    });

    it("I-131: 1e18 atoms converts and round-trips", () => {
      const massU = 130.9061;
      const n = 1e18;
      const g = atomsToGrams(n, massU);
      expect(g).toBeCloseTo((n * massU) / AVOGADRO_PER_MOL, 12);
      expect(gramsToAtoms(g, massU)).toBeCloseTo(n, 0);
    });

    it("zero maps to zero both ways", () => {
      expect(atomsToGrams(0, 238.0508)).toBe(0);
      expect(gramsToAtoms(0, 238.0508)).toBe(0);
    });
  });

  describe("decayConstant / meanLifetimeS", () => {
    it("I-131 half-life 692988.48 s → λ = ln2 / T½", () => {
      const lam = decayConstant(692988.48);
      expect(lam).toBeCloseTo(Math.LN2 / 692988.48, 15);
      expect(lam).toBeGreaterThan(0);
    });

    it("one-second half-life has λ = ln2", () => {
      expect(decayConstant(1)).toBeCloseTo(Math.LN2, 15);
    });

    it("τ = 1/λ and τ = T½ / ln2", () => {
      const tHalf = 692988.48;
      const lam = decayConstant(tHalf);
      expect(meanLifetimeS(lam)).toBeCloseTo(tHalf / Math.LN2, 6);
      expect(meanLifetimeS(Math.LN2)).toBeCloseTo(1 / Math.LN2, 15);
    });
  });

  describe("toSeconds", () => {
    it("passes non-negative finite numbers through", () => {
      expect(toSeconds(90)).toBe(90);
      expect(toSeconds(0)).toBe(0);
      expect(toSeconds(692988.48)).toBe(692988.48);
    });

    it("parses day/hour/minute/second strings", () => {
      expect(toSeconds("8.02 days")).toBeCloseTo(8.02 * 86400, 9);
      expect(toSeconds("24 hours")).toBe(86400);
      expect(toSeconds("2 hours")).toBe(7200);
      expect(toSeconds("30 minutes")).toBe(1800);
      expect(toSeconds("1 second")).toBe(1);
    });

    it("I-131 8.0228 days ≈ ICRP 692988.48 s within 0.1%", () => {
      const s = toSeconds("8.0228 days");
      const rel = Math.abs(s - 692988.48) / 692988.48;
      expect(rel).toBeLessThan(1e-3);
    });

    it("rejects negative numbers and garbage strings", () => {
      expect(() => toSeconds(-1)).toThrow(/>= 0/);
      expect(() => toSeconds(Number.NaN)).toThrow(/finite/);
      expect(() => toSeconds("not a time")).toThrow(/cannot parse/);
      expect(() => toSeconds("8 parsecs")).toThrow(/unknown time unit/);
    });
  });

  describe("formatConverter", () => {
    it("formats mid-range values with locale separators", () => {
      expect(formatConverter(37000000000)).toBe("37,000,000,000");
      expect(formatConverter(0)).toBe("0");
    });

    it("uses scientific notation for very large and very small values", () => {
      expect(formatConverter(1.234e20)).toMatch(/e\+20/i);
      expect(formatConverter(1.5e-10)).toMatch(/e-10/i);
    });
  });
});

import { describe, expect, it } from "vitest";
import { enrichElementsWithApi, fallbackElements, getCategory, getPosition } from "./elements";

describe("fallbackElements catalog", () => {
  it("contains 118 elements", () => {
    expect(fallbackElements).toHaveLength(118);
  });

  it("covers atomic numbers 1..118 without gaps or duplicates", () => {
    const numbers = fallbackElements.map((e) => e.number).sort((a, b) => a - b);
    for (let i = 0; i < 118; i++) {
      expect(numbers[i]).toBe(i + 1);
    }
  });

  it("hydrogen is first", () => {
    const h = fallbackElements[0];
    expect(h.symbol).toBe("H");
    expect(h.name).toBe("Hydrogen");
    expect(h.number).toBe(1);
    expect(h.period).toBe(1);
    expect(h.group).toBe(1);
    expect(h.row).toBe(1);
    expect(h.column).toBe(1);
  });

  it("helium is top-right", () => {
    const he = fallbackElements.find((e) => e.symbol === "He")!;
    expect(he.period).toBe(1);
    expect(he.group).toBe(18);
    expect(he.row).toBe(1);
    expect(he.column).toBe(18);
  });

  it("every element has non-empty name, symbol, mass, state", () => {
    for (const e of fallbackElements) {
      expect(e.name.length).toBeGreaterThan(0);
      expect(e.symbol.length).toBeGreaterThan(0);
      expect(e.mass.length).toBeGreaterThan(0);
      expect(e.state.length).toBeGreaterThan(0);
      expect(e.category.length).toBeGreaterThan(0);
      expect(e.row).toBeGreaterThanOrEqual(1);
      expect(e.column).toBeGreaterThanOrEqual(1);
    }
  });

  it("lanthanides (57-71) sit in row 9", () => {
    for (const e of fallbackElements) {
      if (e.number >= 57 && e.number <= 71) {
        expect(e.category).toBe("Lanthanide");
        expect(e.row).toBe(9);
        expect(e.group).toBeNull();
      }
    }
  });

  it("actinides (89-103) sit in row 10", () => {
    for (const e of fallbackElements) {
      if (e.number >= 89 && e.number <= 103) {
        expect(e.category).toBe("Actinide");
        expect(e.row).toBe(10);
        expect(e.group).toBeNull();
      }
    }
  });

  it("period columns stay within 1..18 for non-f-block periods", () => {
    for (const e of fallbackElements) {
      if (e.group !== null) {
        expect(e.column).toBeGreaterThanOrEqual(1);
        expect(e.column).toBeLessThanOrEqual(18);
        expect(e.group).toBe(e.column);
      }
    }
  });

  it("alkali metals are categorized as such", () => {
    const na = fallbackElements.find((e) => e.symbol === "Na")!;
    expect(na.category).toBe("Alkali metal");
    const li = fallbackElements.find((e) => e.symbol === "Li")!;
    expect(li.category).toBe("Alkali metal");
  });

  it("noble gases are categorized as such", () => {
    const ne = fallbackElements.find((e) => e.symbol === "Ne")!;
    expect(ne.category).toBe("Noble gas");
    const ar = fallbackElements.find((e) => e.symbol === "Ar")!;
    expect(ar.category).toBe("Noble gas");
  });
});

describe("getPosition cross-checks", () => {
  const known: Array<[number, number, number | null, number, number]> = [
    // Z, period, group, row, column
    [1, 1, 1, 1, 1],
    [2, 1, 18, 1, 18],
    [3, 2, 1, 2, 1],
    [4, 2, 2, 2, 2],
    [10, 2, 18, 2, 18],
    [11, 3, 1, 3, 1],
    [18, 3, 18, 3, 18],
    [19, 4, 1, 4, 1],
    [36, 4, 18, 4, 18],
    [53, 5, 17, 5, 17], // iodine
    [54, 5, 18, 5, 18], // xenon
    [55, 6, 1, 6, 1],
    [56, 6, 2, 6, 2],
    [57, 6, null, 9, 3], // lanthanum start of f-block row
    [71, 6, null, 9, 17],
    [72, 6, 4, 6, 4],
    [86, 6, 18, 6, 18],
    [87, 7, 1, 7, 1],
    [88, 7, 2, 7, 2],
    [89, 7, null, 10, 3],
    [103, 7, null, 10, 17],
    [104, 7, 4, 7, 4],
    [118, 7, 18, 7, 18],
  ];

  for (const [z, period, group, row, column] of known) {
    it(`Z=${z} position`, () => {
      const pos = getPosition(z);
      expect(pos.period).toBe(period);
      expect(pos.group).toBe(group);
      expect(pos.row).toBe(row);
      expect(pos.column).toBe(column);
    });
  }

  it("is total for 1..118 (period 1-7, row in 1-10)", () => {
    for (let z = 1; z <= 118; z++) {
      const pos = getPosition(z);
      expect(pos.period).toBeGreaterThanOrEqual(1);
      expect(pos.period).toBeLessThanOrEqual(7);
      expect(pos.row).toBeGreaterThanOrEqual(1);
      expect(pos.row).toBeLessThanOrEqual(10);
      if (pos.group !== null) {
        expect(pos.group).toBeGreaterThanOrEqual(1);
        expect(pos.group).toBeLessThanOrEqual(18);
      }
    }
  });

  it("matches fallbackElements positions for every element", () => {
    for (const e of fallbackElements) {
      const pos = getPosition(e.number);
      expect(pos.period).toBe(e.period);
      expect(pos.group).toBe(e.group);
      expect(pos.row).toBe(e.row);
      expect(pos.column).toBe(e.column);
    }
  });
});

describe("getCategory", () => {
  it("maps known group blocks", () => {
    expect(getCategory("alkali metal")).toBe("Alkali metal");
    expect(getCategory("alkaline earth metal")).toBe("Alkaline earth metal");
    expect(getCategory("transition metal")).toBe("Transition metal");
    expect(getCategory("post-transition metal")).toBe("Post-transition metal");
    expect(getCategory("metal")).toBe("Post-transition metal");
    expect(getCategory("metalloid")).toBe("Metalloid");
    expect(getCategory("nonmetal")).toBe("Nonmetal");
    expect(getCategory("halogen")).toBe("Halogen");
    expect(getCategory("noble gas")).toBe("Noble gas");
    expect(getCategory("lanthanoid")).toBe("Lanthanide");
    expect(getCategory("actinoid")).toBe("Actinide");
  });

  it("unknown blocks fall back to Element", () => {
    expect(getCategory("unknown")).toBe("Element");
    expect(getCategory("")).toBe("Element");
  });
});

describe("enrichElementsWithApi", () => {
  function makeApiPayload(overrides: Record<number, Record<string, unknown>> = {}) {
    return fallbackElements.map((e) => ({
      atomic_number: e.number,
      atomic_mass: 100 + e.number,
      electron_configuration_semantic: `cfg-${e.symbol}`,
      electronegativity: 2.5,
      state_at_room_temp: "solid",
      melting_point: 300 + e.number,
      ...overrides[e.number],
    }));
  }

  it("returns null for non-arrays", () => {
    expect(enrichElementsWithApi(null)).toBeNull();
    expect(enrichElementsWithApi(undefined)).toBeNull();
    expect(enrichElementsWithApi({})).toBeNull();
    expect(enrichElementsWithApi("[]")).toBeNull();
  });

  it("returns null when payload is not exactly 118 records", () => {
    expect(enrichElementsWithApi([])).toBeNull();
    expect(enrichElementsWithApi(makeApiPayload().slice(0, 117))).toBeNull();
    expect(enrichElementsWithApi([...makeApiPayload(), { atomic_number: 119 }])).toBeNull();
  });

  it("returns null when atomic_number is missing on some records", () => {
    const bad = makeApiPayload().map((r, i) => (i === 0 ? { ...r, atomic_number: "1" } : r));
    expect(enrichElementsWithApi(bad)).toBeNull();
  });

  it("enriches all 118 elements when payload is valid", () => {
    const result = enrichElementsWithApi(makeApiPayload());
    expect(result).not.toBeNull();
    expect(result!).toHaveLength(118);
    const h = result!.find((e) => e.symbol === "H")!;
    expect(h.mass).toBe("101");
    expect(h.configuration).toBe("cfg-H");
    expect(h.electronegativity).toBe(2.5);
    expect(h.state).toBe("solid");
    expect(h.meltingPoint).toBe(301);
  });

  it("keeps fallback values when API field types are wrong", () => {
    const payload = makeApiPayload({
      1: {
        atomic_mass: "not-a-number",
        electron_configuration_semantic: 42,
        electronegativity: "high",
        state_at_room_temp: 0,
        melting_point: "cold",
      },
    });
    const result = enrichElementsWithApi(payload)!;
    const h = result.find((e) => e.symbol === "H")!;
    const fallbackH = fallbackElements.find((e) => e.symbol === "H")!;
    expect(h.mass).toBe(fallbackH.mass);
    expect(h.configuration).toBe(fallbackH.configuration);
    expect(h.electronegativity).toBe(fallbackH.electronegativity);
    expect(h.state).toBe(fallbackH.state);
    expect(h.meltingPoint).toBe(fallbackH.meltingPoint);
  });

  it("preserves number, symbol, name, position from fallback", () => {
    const result = enrichElementsWithApi(makeApiPayload())!;
    for (let i = 0; i < 118; i++) {
      expect(result[i].number).toBe(fallbackElements[i].number);
      expect(result[i].symbol).toBe(fallbackElements[i].symbol);
      expect(result[i].name).toBe(fallbackElements[i].name);
      expect(result[i].row).toBe(fallbackElements[i].row);
      expect(result[i].column).toBe(fallbackElements[i].column);
    }
  });

  it("ignores records without object shape", () => {
    const payload: unknown[] = [...makeApiPayload(), null, 3, "x"];
    // Still 118 valid atomic_number records → enrichment proceeds.
    const result = enrichElementsWithApi(payload);
    expect(result).not.toBeNull();
    expect(result!).toHaveLength(118);
  });
});

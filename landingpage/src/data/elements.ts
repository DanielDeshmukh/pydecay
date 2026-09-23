import periodicData from "periodic-table/data.json";

type RawElement = {
  atomicNumber: number;
  symbol: string;
  name: string;
  atomicMass: string | number[];
  electronicConfiguration: string;
  electronegativity: number | string;
  standardState: string;
  meltingPoint: number | string;
  groupBlock: string;
};

export type ElementInfo = {
  number: number;
  symbol: string;
  name: string;
  mass: string;
  configuration: string;
  electronegativity: number | null;
  state: string;
  meltingPoint: number | null;
  category: string;
  period: number;
  group: number | null;
  row: number;
  column: number;
};

function getPosition(number: number) {
  if (number === 1) return { period: 1, group: 1, row: 1, column: 1 };
  if (number === 2) return { period: 1, group: 18, row: 1, column: 18 };

  if (number <= 10) {
    const group = number <= 4 ? number - 2 : number + 8;
    return { period: 2, group, row: 2, column: group };
  }
  if (number <= 18) {
    const group = number <= 12 ? number - 10 : number;
    return { period: 3, group, row: 3, column: group };
  }
  if (number <= 36) {
    const group = number - 18;
    return { period: 4, group, row: 4, column: group };
  }
  if (number <= 54) {
    const group = number - 36;
    return { period: 5, group, row: 5, column: group };
  }
  if (number <= 56) {
    const group = number - 54;
    return { period: 6, group, row: 6, column: group };
  }
  if (number <= 71) {
    return { period: 6, group: null, row: 9, column: number - 54 };
  }
  if (number <= 86) {
    const group = number - 68;
    return { period: 6, group, row: 6, column: group };
  }
  if (number <= 88) {
    const group = number - 86;
    return { period: 7, group, row: 7, column: group };
  }
  if (number <= 103) {
    return { period: 7, group: null, row: 10, column: number - 86 };
  }
  const group = number - 100;
  return { period: 7, group, row: 7, column: group };
}

function getCategory(groupBlock: string) {
  const categories: Record<string, string> = {
    "alkali metal": "Alkali metal",
    "alkaline earth metal": "Alkaline earth metal",
    "transition metal": "Transition metal",
    "post-transition metal": "Post-transition metal",
    metal: "Post-transition metal",
    metalloid: "Metalloid",
    nonmetal: "Nonmetal",
    halogen: "Halogen",
    "noble gas": "Noble gas",
    lanthanoid: "Lanthanide",
    actinoid: "Actinide",
  };
  return categories[groupBlock] ?? "Element";
}

export const fallbackElements: ElementInfo[] = (periodicData as unknown as RawElement[]).map(
  (element) => ({
    number: element.atomicNumber,
    symbol: element.symbol,
    name: element.name,
    mass: Array.isArray(element.atomicMass)
      ? `[${element.atomicMass[0]}]`
      : element.atomicMass.split("(")[0],
    configuration: element.electronicConfiguration || "Not available",
    electronegativity:
      typeof element.electronegativity === "number" ? element.electronegativity : null,
    state: element.standardState || "Unknown",
    meltingPoint: typeof element.meltingPoint === "number" ? element.meltingPoint : null,
    category:
      element.atomicNumber >= 57 && element.atomicNumber <= 71
        ? "Lanthanide"
        : element.atomicNumber >= 89 && element.atomicNumber <= 103
          ? "Actinide"
          : getCategory(element.groupBlock),
    ...getPosition(element.atomicNumber),
  }),
);

// The bundled table is immediate and offline-safe; the public API refreshes measured properties.
export function enrichElementsWithApi(data: unknown): ElementInfo[] | null {
  if (!Array.isArray(data)) return null;

  const records = new Map<number, Record<string, unknown>>();
  for (const record of data) {
    if (record && typeof record === "object" && typeof record.atomic_number === "number") {
      records.set(record.atomic_number, record as Record<string, unknown>);
    }
  }
  if (records.size !== 118) return null;

  return fallbackElements.map((element) => {
    const record = records.get(element.number);
    if (!record) return element;
    return {
      ...element,
      mass:
        typeof record.atomic_mass === "number"
          ? String(record.atomic_mass)
          : element.mass,
      configuration:
        typeof record.electron_configuration_semantic === "string"
          ? record.electron_configuration_semantic
          : element.configuration,
      electronegativity:
        typeof record.electronegativity === "number"
          ? record.electronegativity
          : element.electronegativity,
      state:
        typeof record.state_at_room_temp === "string"
          ? record.state_at_room_temp
          : element.state,
      meltingPoint:
        typeof record.melting_point === "number"
          ? record.melting_point
          : element.meltingPoint,
    };
  });
}
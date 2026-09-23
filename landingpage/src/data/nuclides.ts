export type DemoNuclide = {
  id: string;
  element: string;
  halfLifeDays: number;
  displayHalfLife: string;
  timeUnit: "hours" | "days" | "years";
  daysPerUnit: number;
};

// Half-lives are representative IAEA recommended values, expressed in days internally.
export const demoNuclides: DemoNuclide[] = [
  {
    id: "I-131",
    element: "Iodine",
    halfLifeDays: 8.0228,
    displayHalfLife: "8.0228 days",
    timeUnit: "days",
    daysPerUnit: 1,
  },
  {
    id: "Co-60",
    element: "Cobalt",
    halfLifeDays: 1925.23,
    displayHalfLife: "5.27 years",
    timeUnit: "years",
    daysPerUnit: 365.2422,
  },
  {
    id: "Cs-137",
    element: "Cesium",
    halfLifeDays: 10990,
    displayHalfLife: "30.09 years",
    timeUnit: "years",
    daysPerUnit: 365.2422,
  },
  {
    id: "Tc-99m",
    element: "Technetium",
    halfLifeDays: 0.250281,
    displayHalfLife: "6.01 hours",
    timeUnit: "hours",
    daysPerUnit: 1 / 24,
  },
];

export const featuredIsotopes: Record<string, string> = {
  I: "I-131",
  Co: "Co-60",
  Cs: "Cs-137",
  Tc: "Tc-99m",
};

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "./App";

// jsdom lacks IntersectionObserver (framer-motion whileInView) and matchMedia is partial.
class MockIntersectionObserver {
  root = null;
  rootMargin = "";
  thresholds: number[] = [];
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

beforeEach(() => {
  vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);
  if (!window.matchMedia) {
    vi.stubGlobal(
      "matchMedia",
      vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    );
  }
  // Silence fetch network noise; individual tests override as needed.
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network disabled in tests")));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function stubLocation(path: string) {
  Object.defineProperty(window, "location", {
    value: { pathname: path, origin: "http://localhost", href: `http://localhost${path}` },
    writable: true,
    configurable: true,
  });
}

describe("App home page", () => {
  it("renders hero and playground by default", () => {
    stubLocation("/");
    render(<App />);
    expect(screen.getByRole("heading", { name: /pydecay/i })).toBeTruthy();
    expect(screen.getByText(/SEE TIME DO ITS WORK/i)).toBeTruthy();
    expect(screen.getByRole("combobox", { name: "NUCLIDE" })).toBeTruthy();
  });

  it("renders unit converter playground with live Bq to Ci", () => {
    stubLocation("/");
    render(<App />);
    expect(screen.getByText(/UNITS, IN REAL TIME/i)).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Bq ↔ Ci" })).toBeTruthy();
    expect(screen.getAllByLabelText(/^ACTIVITY$/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByDisplayValue("3.7e10")).toBeTruthy();
    expect(screen.getAllByText(/37,000,000,000/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/bq_to_ci/).length).toBeGreaterThan(0);
  });

  it("switches unit converter to time mode and shows seconds", () => {
    stubLocation("/");
    render(<App />);
    fireEvent.click(screen.getByRole("tab", { name: "time → s" }));
    expect(screen.getByLabelText(/^TIME$/i)).toBeTruthy();
    expect(screen.getAllByText(/692,928/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/to_seconds/).length).toBeGreaterThan(0);
  });

  it("switches unit converter to decay mode and shows lambda", () => {
    stubLocation("/");
    render(<App />);
    fireEvent.click(screen.getByRole("tab", { name: "T½ → λ, τ" }));
    expect(screen.getByLabelText(/HALF-LIFE/i)).toBeTruthy();
    expect(screen.getAllByText(/decay_constant/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/mean_lifetime_s/).length).toBeGreaterThan(0);
  });

  it("shows I-131 default playground activity of 500 Bq after one half-life", () => {
    stubLocation("/");
    render(<App />);
    expect(screen.getAllByText(/500\.00/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/50\.00% of the initial activity remains/)).toBeTruthy();
  });

  it("updates remaining activity when slider moves to 2 half-lives", () => {
    stubLocation("/");
    render(<App />);
    const slider = screen.getByLabelText(/TIME ELAPSED/i);
    fireEvent.change(slider, { target: { value: "2" } });
    expect(screen.getAllByText(/250\.00/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/25\.00% of the initial activity remains/)).toBeTruthy();
  });

  it("updates when initial activity changes", () => {
    stubLocation("/");
    render(<App />);
    const input = screen.getByLabelText(/INITIAL ACTIVITY/i);
    fireEvent.change(input, { target: { value: "2000" } });
    expect(screen.getAllByText(/1,000\.00/).length).toBeGreaterThanOrEqual(2);
  });

  it("resets invalid activity on blur", () => {
    stubLocation("/");
    render(<App />);
    const input = screen.getByLabelText(/INITIAL ACTIVITY/i) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "0" } });
    fireEvent.blur(input);
    expect(input.value).toBe("1000");
  });

  it("switches nuclide via select and updates half-life hint", () => {
    stubLocation("/");
    render(<App />);
    const select = screen.getByRole("combobox", { name: "NUCLIDE" }) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "Co-60" } });
    expect(screen.getByText(/Half-life: 5\.27 years/)).toBeTruthy();
  });

  it("switches playground to the dose tab and shows a live dose rate", () => {
    stubLocation("/");
    render(<App />);
    fireEvent.click(screen.getByRole("tab", { name: "DOSE" }));
    expect(screen.getByText("AIR KERMA RATE")).toBeTruthy();
    expect(screen.getByLabelText("SOURCE NUCLIDE")).toBeTruthy();
    expect(screen.getByText(/Photon-free \(/)).toBeTruthy();
    expect(screen.getAllByText(/dose_rate\(/).length).toBeGreaterThan(0);
  });

  it("toggles the dose quantity to ambient", () => {
    stubLocation("/");
    render(<App />);
    fireEvent.click(screen.getByRole("tab", { name: "DOSE" }));
    const toggle = screen.getByRole("button", { name: /AMBIENT/ });
    fireEvent.click(toggle);
    expect(screen.getByText("AMBIENT DOSE RATE")).toBeTruthy();
    expect(toggle.getAttribute("aria-pressed")).toBe("true");
  });

  it("switches playground to the shielding tab and computes transmission", () => {
    stubLocation("/");
    render(<App />);
    fireEvent.click(screen.getByRole("tab", { name: "SHIELDING" }));
    expect(screen.getByText("TRANSMITTED INTENSITY")).toBeTruthy();
    expect(screen.getByLabelText("SHIELD MATERIAL")).toBeTruthy();
    expect(screen.getByText(/HVL =/)).toBeTruthy();
    expect(screen.getAllByText(/transmit_slab\(/).length).toBeGreaterThan(0);
  });

  it("renders navigation links", () => {
    stubLocation("/");
    render(<App />);
    const nav = screen.getAllByRole("navigation");
    expect(nav.length).toBeGreaterThan(0);
    expect(screen.getAllByText("OVERVIEW").length).toBeGreaterThan(0);
    expect(screen.getAllByText("PLAYGROUND").length).toBeGreaterThan(0);
    expect(screen.getAllByText("ELEMENTS").length).toBeGreaterThan(0);
    expect(screen.getAllByText("DOCS").length).toBeGreaterThan(0);
  });

  it("renders periodic table section with 118-element claim", () => {
    stubLocation("/");
    render(<App />);
    expect(screen.getByText(/118 ELEMENTS/)).toBeTruthy();
    expect(screen.getByText(/pydecay bundles 1252 ICRP-107 radionuclides/)).toBeTruthy();
  });

  it("renders verification section", () => {
    stubLocation("/");
    render(<App />);
    expect(screen.getByText(/NUMBERS YOU CAN DEFEND/i)).toBeTruthy();
    expect(screen.getByText(/Known values, independently asserted\./)).toBeTruthy();
  });

  it("expands a verification row when + is clicked", () => {
    stubLocation("/");
    render(<App />);
    const button = screen.getByRole("button", { name: /Expand test 01/i });
    fireEvent.click(button);
    expect(button.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText(/tests\/test_known_values\.py/)).toBeTruthy();
  });

  it("toggles feature tabs in capabilities", () => {
    stubLocation("/");
    render(<App />);
    const tab = screen.getByRole("tab", { name: /Decay chains/i });
    fireEvent.click(tab);
    expect(tab.getAttribute("aria-selected")).toBe("true");
    expect(screen.getByText(/Bateman's closed form/)).toBeTruthy();
  });

  it("fetch failure keeps bundled elements (no crash)", async () => {
    stubLocation("/");
    // fetch already stubbed to reject in beforeEach
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/BUNDLED REFERENCE DATA/)).toBeTruthy();
    });
  });
});

describe("App docs page", () => {
  it("renders docs masthead and installation section", () => {
    stubLocation("/docs");
    render(<App />);
    expect(screen.getByRole("heading", { name: /Documentation/i })).toBeTruthy();
    expect(screen.getByText(/VERSION 0\.6\.0/)).toBeTruthy();
    expect(screen.getByText(/pip install pydecay/)).toBeTruthy();
  });

  it("lists all 11 doc contents entries", () => {
    stubLocation("/docs");
    render(<App />);
    expect(screen.getByText(/CONTENTS \/ 11/)).toBeTruthy();
    for (const label of [
      "Installation",
      "User guide",
      "Quickstart",
      "Single isotope",
      "Decay chains",
      "Branching",
      "Spectra",
      "Solver strategy",
      "Data & units",
      "Verification",
      "Changelog",
    ]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
  });

  it("shows user guide function coverage", () => {
    stubLocation("/docs/user-guide");
    render(<App />);
    expect(screen.getAllByText(/decayed_activity/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/decayed_atoms/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/remaining_fraction/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/NuclideNotFoundError/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/to_seconds/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/bq_to_ci/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/atoms_to_grams/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/decay_constant/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/mean_lifetime_s/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/dn_dt/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/da_dt/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/decay_ode_residual/).length).toBeGreaterThan(0);
  });

  it("shows changelog with current 0.6.0 entry", () => {
    stubLocation("/docs/changelog");
    render(<App />);
    expect(screen.getAllByText(/0\.6\.0/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/DoseDataError/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0\.5\.1/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ICRP-107 catalog counting/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0\.5\.0/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/instantaneous rates/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0\.4\.0/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/top-level re-exports/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0\.3\.0/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0\.2\.0/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/^Changelog$/).length).toBeGreaterThan(0);
  });

  it("shows contributor quality gates", () => {
    stubLocation("/docs/verification");
    render(<App />);
    expect(screen.getAllByText(/mkdocs build --strict/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ruff check src tests/).length).toBeGreaterThan(0);
  });
});

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
    expect(screen.getByText(/VERSION 0\.2\.0/)).toBeTruthy();
    expect(screen.getByText(/pip install pydecay/)).toBeTruthy();
  });

  it("lists all 10 doc contents entries", () => {
    stubLocation("/docs");
    render(<App />);
    expect(screen.getByText(/CONTENTS \/ 10/)).toBeTruthy();
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
  });

  it("shows contributor quality gates", () => {
    stubLocation("/docs/verification");
    render(<App />);
    expect(screen.getAllByText(/mkdocs build --strict/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ruff check src tests/).length).toBeGreaterThan(0);
  });
});

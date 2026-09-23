import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import CodeBlock from "./CodeBlock";

afterEach(cleanup);

describe("CodeBlock", () => {
  it("renders the code and default label", () => {
    render(<CodeBlock code="print(1)" />);
    expect(screen.getByText("PYTHON")).toBeTruthy();
    expect(screen.getByText(/print/)).toBeTruthy();
  });

  it("renders a custom label", () => {
    render(<CodeBlock code="x = 1" label="TERMINAL" />);
    expect(screen.getByText("TERMINAL")).toBeTruthy();
  });

  it("applies compact and custom className", () => {
    const { container } = render(<CodeBlock code="y = 2" compact className="workbench-code" />);
    const root = container.querySelector(".code-block");
    expect(root?.classList.contains("code-block-compact")).toBe(true);
    expect(root?.classList.contains("workbench-code")).toBe(true);
  });

  it("copy button starts as COPY and is accessible", () => {
    render(<CodeBlock code="z = 3" />);
    const button = screen.getByRole("button", { name: /copy code/i });
    expect(button.textContent).toContain("COPY");
  });

  it("attempting copy without clipboard API does not throw", () => {
    // jsdom lacks clipboard in some setups; handler must fail soft.
    render(<CodeBlock code="w = 4" />);
    const button = screen.getByRole("button", { name: /copy code/i });
    expect(() => fireEvent.click(button)).not.toThrow();
  });
});

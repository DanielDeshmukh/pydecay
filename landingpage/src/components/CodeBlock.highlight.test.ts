import { describe, expect, it } from "vitest";

const tokenPattern =
  /(#[^\n]*|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\b(?:from|import|print|None|True|False)\b|\b\d+(?:\.\d+)?(?:e[+-]?\d+)?\b)/gi;

/** Mirrors CodeBlock's private highlight tokenizer for cross-check tests. */
function highlightParts(code: string): Array<{ text: string; kind: string }> {
  return code
    .split(tokenPattern)
    .filter((part) => part !== undefined && part !== "")
    .map((part) => {
      let kind = "plain";
      if (part.startsWith("#")) kind = "token-comment";
      else if (part.startsWith('"') || part.startsWith("'")) kind = "token-string";
      else if (/^(from|import|print|None|True|False)$/i.test(part)) kind = "token-keyword";
      else if (/^\d/.test(part)) kind = "token-number";
      return { text: part, kind };
    });
}

describe("CodeBlock token pattern cross-checks", () => {
  it("flags Python keywords", () => {
    const parts = highlightParts("from pydecay import Nuclide");
    const keywords = parts.filter((p) => p.kind === "token-keyword").map((p) => p.text);
    expect(keywords).toContain("from");
    expect(keywords).toContain("import");
  });

  it("flags comments", () => {
    const parts = highlightParts("# 500 Bq after one half-life");
    expect(parts[0].kind).toBe("token-comment");
    expect(parts[0].text).toContain("500 Bq");
  });

  it("flags string literals", () => {
    const parts = highlightParts('Nuclide.load("I-131")');
    const strings = parts.filter((p) => p.kind === "token-string");
    expect(strings).toHaveLength(1);
    expect(strings[0].text).toBe('"I-131"');
  });

  it("flags numbers including decimals and scientific notation", () => {
    const parts = highlightParts("A0=1000.0 half_life=1e-5");
    const numbers = parts.filter((p) => p.kind === "token-number").map((p) => p.text);
    expect(numbers).toContain("1000.0");
    expect(numbers).toContain("1e-5");
  });

  it("reassembles the original code when parts are joined", () => {
    const code = "from pydecay import decayed_activity\n# note\nprint(500.0)";
    const joined = highlightParts(code)
      .map((p) => p.text)
      .join("");
    expect(joined).toBe(code);
  });
});

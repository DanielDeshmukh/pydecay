import { useEffect, useRef, useState } from "react";
import { Check, Copy } from "lucide-react";

type CodeBlockProps = {
  code: string;
  label?: string;
  compact?: boolean;
  className?: string;
};

const tokenPattern = /(#[^\n]*|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\b(?:from|import|print|None|True|False)\b|\b\d+(?:\.\d+)?(?:e[+-]?\d+)?\b)/gi;

function highlight(code: string) {
  return code.split(tokenPattern).map((part, index) => {
    let className = "";
    if (part.startsWith("#")) className = "token-comment";
    else if (part.startsWith('"') || part.startsWith("'")) className = "token-string";
    else if (/^(from|import|print|None|True|False)$/i.test(part)) className = "token-keyword";
    else if (/^\d/.test(part)) className = "token-number";

    return className ? (
      <span className={className} key={index}>
        {part}
      </span>
    ) : (
      part
    );
  });
}

async function copyToClipboard(text: string) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const field = document.createElement("textarea");
  field.value = text;
  field.style.position = "fixed";
  field.style.opacity = "0";
  document.body.appendChild(field);
  field.select();
  document.execCommand("copy");
  field.remove();
}

export default function CodeBlock({ code, label = "PYTHON", compact = false, className = "" }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const timeout = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timeout.current), []);

  async function handleCopy() {
    try {
      await copyToClipboard(code);
      setCopied(true);
      window.clearTimeout(timeout.current);
      timeout.current = window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className={`code-block ${compact ? "code-block-compact" : ""} ${className}`}>
      <div className="code-block-header">
        <span>{label}</span>
        <button type="button" onClick={handleCopy} className="code-copy" aria-label={copied ? "Code copied" : "Copy code"}>
          {copied ? <Check size={14} /> : <Copy size={14} />}
          <span>{copied ? "COPIED" : "COPY"}</span>
        </button>
      </div>
      <pre><code>{highlight(code)}</code></pre>
    </div>
  );
}
import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { AnimatePresence, motion, MotionConfig } from "framer-motion";
import {
  ArrowRight,
  ArrowUpRight,
  ChevronDown,
  ExternalLink,
  GitBranch,
  Menu,
  Search,
  X,
} from "lucide-react";
import CodeBlock from "./components/CodeBlock";
import { enrichElementsWithApi, fallbackElements, type ElementInfo } from "./data/elements";
import { demoNuclides, featuredIsotopes } from "./data/nuclides";

const GITHUB_URL = "https://github.com/DanielDeshmukh/pydecay";
const PYPI_URL = "https://pypi.org/project/pydecay/";
// Mirrors --accent in index.css; SVG presentation attributes can't read CSS variables.
const ACCENT = "#55b0f3";

function LogoMark() {
  return (
    <span className="logo-mark" aria-hidden="true">
      <svg viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="16" r="11.5" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="16" cy="16" r="5" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="16" cy="16" r="1.8" fill="currentColor" />
        <path d="M16 0v8M16 24v8M0 16h8M24 16h8" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    </span>
  );
}

function SiteHeader({ hash }: { hash: string }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const isDocs = hash.startsWith("#/docs");
  const links = [
    { label: "OVERVIEW", href: "#/", active: hash === "#/" || hash === "#top" },
    { label: "PLAYGROUND", href: "#playground", active: hash === "#playground" },
    { label: "ELEMENTS", href: "#elements", active: hash === "#elements" },
    { label: "DOCS", href: "#/docs", active: isDocs },
  ];

  return (
    <header className="site-header">
      <div className="header-inner">
        <a href="#/" className="brand-link" onClick={() => setMenuOpen(false)} aria-label="pydecay home">
          <LogoMark />
          <span>pydecay<span className="brand-period">.</span></span>
        </a>

        <nav className="desktop-nav" aria-label="Main navigation">
          {links.map((link) => (
            <a className={link.active ? "nav-active" : ""} href={link.href} key={link.label}>
              {link.label}
            </a>
          ))}
        </nav>

        <a className="header-github" href={GITHUB_URL} target="_blank" rel="noreferrer noopener">
          <GitBranch size={16} strokeWidth={1.8} />
          <span>GITHUB</span>
          <ArrowUpRight size={15} strokeWidth={1.8} />
        </a>

        <button
          type="button"
          className="menu-toggle"
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? <X size={23} /> : <Menu size={23} />}
        </button>
      </div>

      {menuOpen && (
        <nav className="mobile-nav" aria-label="Mobile navigation">
          {links.map((link) => (
            <a href={link.href} key={link.label} onClick={() => setMenuOpen(false)}>
              {link.label}<ArrowUpRight size={18} />
            </a>
          ))}
          <a href={GITHUB_URL} target="_blank" rel="noreferrer noopener" onClick={() => setMenuOpen(false)}>
            GITHUB<ArrowUpRight size={18} />
          </a>
        </nav>
      )}
    </header>
  );
}

function Reveal({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.12 }}
      transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

function decayPath(x: number, top: number, bottom: number, width: number, halfLives: number) {
  return Array.from({ length: 101 }, (_, index) => {
    const progress = index / 100;
    const px = x + width * progress;
    const py = bottom - (bottom - top) * Math.pow(0.5, halfLives * progress);
    return `${index === 0 ? "M" : "L"}${px.toFixed(2)} ${py.toFixed(2)}`;
  }).join(" ");
}

function HeroPlot() {
  const mainPath = decayPath(570, 140, 650, 900, 5);

  return (
    <svg className="hero-plot" viewBox="0 0 1440 760" preserveAspectRatio="xMidYMid slice" role="img" aria-label="A plotted exponential radioactive decay curve over five half-lives">
      <defs>
        <linearGradient id="hero-curve-fill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={ACCENT} stopOpacity="0.16" />
          <stop offset="100%" stopColor={ACCENT} stopOpacity="0" />
        </linearGradient>
        <filter id="hero-line-glow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="5" />
        </filter>
      </defs>

      <g className="hero-grid-lines">
        {[570, 750, 930, 1110, 1290, 1470].map((x) => <line key={`v-${x}`} x1={x} x2={x} y1="115" y2="650" />)}
        {[140, 242, 344, 446, 548, 650].map((y) => <line key={`h-${y}`} x1="570" x2="1470" y1={y} y2={y} />)}
      </g>
      <path d="M570 650H1470" stroke="#6c6f70" strokeWidth="1" />
      <path d="M570 115V650" stroke="#6c6f70" strokeWidth="1" />
      <path d={decayPath(570, 140, 650, 900, 2.35)} className="hero-ghost-curve" />
      <path d={decayPath(570, 140, 650, 900, 9)} className="hero-ghost-curve second" />
      <path d={`${mainPath} L1470 650 L570 650 Z`} fill="url(#hero-curve-fill)" />
      <motion.path
        d={mainPath}
        fill="none"
        stroke={ACCENT}
        strokeWidth="9"
        opacity="0.3"
        filter="url(#hero-line-glow)"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 2, delay: 0.42, ease: "easeOut" }}
      />
      <motion.path
        d={mainPath}
        fill="none"
        stroke={ACCENT}
        strokeWidth="2.5"
        strokeLinecap="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 2, delay: 0.42, ease: "easeOut" }}
      />
      <path d="M750 395V650M570 395H750" stroke={ACCENT} strokeWidth="1" strokeDasharray="5 7" opacity="0.55" />
      <motion.circle
        cx="750"
        cy="395"
        r="6"
        fill={ACCENT}
        stroke="#101113"
        strokeWidth="3"
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 1.2, duration: 0.5 }}
      />
      <g className="hero-chart-type">
        <text x="592" y="102">ACTIVITY / A(t)</text>
        <text x="1400" y="702" textAnchor="end">TIME / HALF-LIVES</text>
        <text x="750" y="680" textAnchor="middle">1</text>
        <text x="930" y="680" textAnchor="middle">2</text>
        <text x="1110" y="680" textAnchor="middle">3</text>
        <text x="1290" y="680" textAnchor="middle">4</text>
        <text x="715" y="375">t1/2</text>
      </g>
    </svg>
  );
}

function Hero() {
  return (
    <section className="hero" id="top">
      <HeroPlot />
      <div className="hero-plot-shade" />
      <div className="hero-copy page-gutter">
        <motion.div initial={{ opacity: 0, y: 28 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.75, delay: 0.1 }}>
          <span className="hero-overline"><span className="live-square" /> OPEN-SOURCE SCIENTIFIC PYTHON</span>
          <h1>pydecay<span>.</span></h1>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 28 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.75, delay: 0.32 }}>
          <h2>Model what remains.</h2>
          <p>Radioactive decay mathematics for Python. From a single isotope to branching decay chains, with precision built in.</p>
          <div className="hero-actions">
            <a href="#/docs" className="button-primary">READ THE DOCS <ArrowUpRight size={18} /></a>
            <a href="#playground" className="text-link">EXPLORE THE PLAYGROUND <ArrowRight size={17} /></a>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function SectionHeading({ number, label, title, description }: { number: string; label: string; title: string; description: string }) {
  return (
    <Reveal className="section-heading">
      <div className="section-heading-left">
        <span className="section-kicker"><span>{number} /</span> {label}</span>
        <h2>{title}</h2>
      </div>
      <p>{description}</p>
    </Reveal>
  );
}

function formatActivity(value: number) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: value >= 10 ? 2 : value >= 1 ? 3 : 6,
    minimumFractionDigits: value >= 10 ? 2 : 0,
  }).format(value);
}

function formatAxis(value: number) {
  if (value === 0) return "0";
  if (value >= 1000) return `${(value / 1000).toFixed(value % 1000 === 0 ? 0 : 1)}k`;
  if (value >= 10) return String(Math.round(value));
  return value.toFixed(value >= 1 ? 1 : 2);
}

function formatTimeTick(value: number) {
  if (value === 0) return "0";
  if (value >= 10) return String(Math.round(value));
  return value.toFixed(1);
}

function Playground({ selectedId, onSelect }: { selectedId: string; onSelect: (id: string) => void }) {
  const [activityInput, setActivityInput] = useState("1000");
  const [halfLives, setHalfLives] = useState(1);
  const nuclide = demoNuclides.find((item) => item.id === selectedId) ?? demoNuclides[0];
  const parsedActivity = Number(activityInput);
  const initialActivity = Number.isFinite(parsedActivity) && parsedActivity > 0 ? parsedActivity : 1000;
  const initialLiteral = Number.isInteger(initialActivity) && !String(initialActivity).includes("e")
    ? `${initialActivity}.0`
    : String(initialActivity);
  const remaining = Math.pow(0.5, halfLives);
  const activity = initialActivity * remaining;
  const elapsedTime = (halfLives * nuclide.halfLifeDays) / nuclide.daysPerUnit;
  const chartPath = decayPath(62, 58, 330, 650, 5);
  const markerX = 62 + (650 * halfLives) / 5;
  const markerY = 330 - 272 * remaining;
  const code = `from pydecay import Nuclide, decayed_activity\n\nnuclide = Nuclide.load("${nuclide.id}")\nactivity = decayed_activity(\n    A0=${initialLiteral},\n    half_life=nuclide.half_life,\n    time=${halfLives.toFixed(2)} * nuclide.half_life,\n)  # ${formatActivity(activity)} Bq`;

  return (
    <section className="playground-section section-shell" id="playground">
      <SectionHeading
        number="01"
        label="THE PLAYGROUND"
        title="See time do its work."
        description="Choose a nuclide, set the starting activity, and watch the decay equation come to life. This browser preview mirrors the single-isotope mathematics."
      />
      <Reveal className="workbench">
        <div className="workbench-controls">
          <div className="workbench-caption"><span className="caption-square" /> INPUT PARAMETERS <span>01 / 03</span></div>

          <label className="field-label" htmlFor="nuclide-select">NUCLIDE</label>
          <div className="select-wrap">
            <select id="nuclide-select" value={nuclide.id} onChange={(event) => onSelect(event.target.value)}>
              {demoNuclides.map((item) => <option key={item.id} value={item.id}>{item.id} / {item.element}</option>)}
            </select>
            <ChevronDown size={17} aria-hidden="true" />
          </div>
          <p className="field-hint">Half-life: {nuclide.displayHalfLife}</p>

          <label className="field-label activity-label" htmlFor="initial-activity">INITIAL ACTIVITY</label>
          <div className="number-wrap">
            <input
              id="initial-activity"
              type="number"
              min="1"
              step="any"
              value={activityInput}
              onChange={(event) => setActivityInput(event.target.value)}
              onBlur={() => {
                if (!Number.isFinite(Number(activityInput)) || Number(activityInput) <= 0) setActivityInput("1000");
              }}
            />
            <span>Bq</span>
          </div>

          <div className="time-label-row">
            <label className="field-label" htmlFor="time-slider">TIME ELAPSED</label>
            <span>{elapsedTime.toFixed(2)} {nuclide.timeUnit}</span>
          </div>
          <input
            className="time-slider"
            id="time-slider"
            type="range"
            min="0"
            max="5"
            step="0.01"
            value={halfLives}
            style={{ "--slider-progress": `${(halfLives / 5) * 100}%` } as CSSProperties}
            onChange={(event) => setHalfLives(Number(event.target.value))}
            aria-valuetext={`${elapsedTime.toFixed(2)} ${nuclide.timeUnit}, ${halfLives.toFixed(2)} half-lives`}
          />
          <div className="range-ends"><span>0</span><span>5 HALF-LIVES</span></div>

          <div className="result-readout" aria-live="polite">
            <span>ACTIVITY REMAINING</span>
            <div>{formatActivity(activity)} <small>Bq</small></div>
            <p>{(remaining * 100).toFixed(2)}% of the initial activity remains</p>
          </div>
        </div>

        <div className="workbench-output">
          <div className="output-topline"><span>DECAY CURVE <i /> {nuclide.id}</span><span>A(t) = A0 * 2<sup>-t / t1/2</sup></span></div>
          <div className="chart-wrap">
            <svg viewBox="0 0 760 410" preserveAspectRatio="xMidYMid meet" role="img" aria-label={`${nuclide.id} decay curve, ${formatActivity(activity)} becquerels remaining after ${elapsedTime.toFixed(2)} ${nuclide.timeUnit}`}>
              <defs>
                <linearGradient id="workbench-area" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor={ACCENT} stopOpacity="0.14" />
                  <stop offset="100%" stopColor={ACCENT} stopOpacity="0" />
                </linearGradient>
              </defs>
              {[58, 126, 194, 262, 330].map((y, index) => (
                <g key={y}>
                  <line className="chart-grid-line" x1="62" x2="712" y1={y} y2={y} />
                  <text className="chart-tick" x="48" y={y + 4} textAnchor="end">{formatAxis(initialActivity * (1 - index / 4))}</text>
                </g>
              ))}
              {Array.from({ length: 6 }, (_, index) => {
                const x = 62 + index * 130;
                return (
                  <g key={index}>
                    <line className="chart-grid-line vertical" x1={x} x2={x} y1="58" y2="330" />
                    <text className="chart-tick" x={x} y="361" textAnchor="middle">
                      {formatTimeTick((index * nuclide.halfLifeDays) / nuclide.daysPerUnit)}
                    </text>
                  </g>
                );
              })}
              <path d={`${chartPath} L712 330 L62 330 Z`} fill="url(#workbench-area)" />
              <path d={chartPath} fill="none" stroke="#4a667d" strokeWidth="2" />
              <motion.path
                d={chartPath}
                fill="none"
                stroke={ACCENT}
                strokeWidth="3"
                strokeLinecap="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: halfLives / 5 }}
                transition={{ duration: 0.55, ease: "easeOut" }}
              />
              <motion.line
                className="chart-marker-line"
                y1="58"
                y2="330"
                initial={false}
                animate={{ x1: markerX, x2: markerX }}
                transition={{ duration: 0.4, ease: "easeOut" }}
              />
              <motion.circle
                r="7"
                fill={ACCENT}
                stroke="#151617"
                strokeWidth="3"
                initial={false}
                animate={{ cx: markerX, cy: markerY }}
                transition={{ duration: 0.4, ease: "easeOut" }}
              />
              <text className="chart-axis-title" x="62" y="24">ACTIVITY / Bq</text>
              <text className="chart-axis-title" x="712" y="400" textAnchor="end">TIME / {nuclide.timeUnit.toUpperCase()}</text>
            </svg>
          </div>
          <CodeBlock code={code} label="GENERATED PYTHON" compact className="workbench-code" />
        </div>
      </Reveal>
      <p className="workbench-footnote">Preview calculated in your browser. Run the generated code with pydecay for your Python workflow.</p>
    </section>
  );
}

type Feature = {
  number: string;
  title: string;
  summary: string;
  tag: string;
  detail: string;
  code: string;
  graphic: "single" | "chain" | "stability" | "branching";
};

const features: Feature[] = [
  {
    number: "01",
    title: "Single isotope",
    summary: "The clean, analytical answer.",
    tag: "ANALYTICAL DECAY",
    detail: "Calculate remaining atoms, fractions, and activity directly from a half-life.",
    code: `from pydecay import Nuclide, decayed_activity\n\ni131 = Nuclide.load("I-131")\na = decayed_activity(A0=1000.0, half_life=i131.half_life, time=i131.half_life)\n# 500 Bq after one half-life`,
    graphic: "single",
  },
  {
    number: "02",
    title: "Decay chains",
    summary: "Follow every daughter through time.",
    tag: "LINEAR SYSTEMS",
    detail: "Bateman's closed form handles well-separated linear chains, all the way to a stable daughter.",
    code: `from pydecay import DecayChain\n\nchain = DecayChain([0.693, 0.0], names=["parent", "stable"])\nprint(chain.at(t="1 days", n0={"parent": 1e6, "stable": 0.0}))`,
    graphic: "chain",
  },
  {
    number: "03",
    title: "Numerical stability",
    summary: "Reliable even when rates converge.",
    tag: "MATRIX EXPONENTIAL",
    detail: "Near-degenerate decay constants, branching, and nonzero daughter populations dispatch to scipy.linalg.expm.",
    code: `from pydecay import DecayChain\n\nchain = DecayChain([0.6931, 0.6932, 0.0], names=["P", "D", "S"])\nchain.at(t=1.0, n0={"P": 1e6, "D": 0.0, "S": 0.0})`,
    graphic: "stability",
  },
  {
    number: "04",
    title: "Branching paths",
    summary: "One parent. Multiple outcomes.",
    tag: "BRANCHING TOPOLOGIES",
    detail: "Model star-shaped branches with fractions up to one; any remainder flows to an untracked sink.",
    code: `from pydecay import DecayChain\n\nb = DecayChain.branching(\n    parent="P", branches={"D1": 0.6, "D2": 0.3},\n    lambdas={"P": 0.7, "D1": 1e-5, "D2": 2e-5},\n)`,
    graphic: "branching",
  },
];

function FeatureGraphic({ type }: { type: Feature["graphic"] }) {
  if (type === "single") {
    return (
      <div className="formula-graphic" aria-label="Exponential single-isotope decay formula">
        <span className="formula-small">THE FUNDAMENTAL EQUATION</span>
        <div>N(t) <em>=</em> N<sub>0</sub> e<sup>-&lambda;t</sup></div>
        <span className="formula-bottom">&lambda; = ln(2) / t<sub>1/2</sub> &nbsp;&nbsp; A(t) = &lambda;N(t)</span>
      </div>
    );
  }

  if (type === "stability") {
    return (
      <div className="formula-graphic stability-graphic" aria-label="Matrix exponential solver formula">
        <span className="formula-small">WHEN CLOSED FORM NEEDS A GUARD</span>
        <div>n(t) <em>=</em> e<sup>Mt</sup> n<sub>0</sub></div>
        <span className="formula-bottom">NEAR-EQUAL RATES / FINITE RESULTS / NO CANCELLATION</span>
      </div>
    );
  }

  if (type === "chain") {
    return (
      <svg className="topology-graphic" viewBox="0 0 640 200" role="img" aria-label="Parent nuclide decays into daughter and then stable nuclide">
        <path d="M150 93H258M373 93H482" className="topology-line" />
        <path d="m250 85 10 8-10 8m224-16 10 8-10 8" className="topology-arrow" />
        <rect x="34" y="48" width="116" height="90" className="topology-node active" />
        <rect x="258" y="48" width="116" height="90" className="topology-node" />
        <rect x="482" y="48" width="116" height="90" className="topology-node" />
        <text x="92" y="100" textAnchor="middle" className="topology-symbol active-text">P</text>
        <text x="316" y="100" textAnchor="middle" className="topology-symbol">D</text>
        <text x="540" y="100" textAnchor="middle" className="topology-symbol">S</text>
        <text x="92" y="161" textAnchor="middle" className="topology-caption">PARENT</text>
        <text x="316" y="161" textAnchor="middle" className="topology-caption">DAUGHTER</text>
        <text x="540" y="161" textAnchor="middle" className="topology-caption">STABLE</text>
      </svg>
    );
  }

  return (
    <svg className="topology-graphic branching-graphic" viewBox="0 0 640 200" role="img" aria-label="A parent branches to two daughters at 60 and 30 percent">
      <path d="M150 97H260L377 45H480M260 97l117 65h103" className="topology-line" />
      <path d="M472 37l10 8-10 8M472 154l10 8-10 8" className="topology-arrow" />
      <rect x="34" y="52" width="116" height="90" className="topology-node active" />
      <rect x="480" y="12" width="116" height="68" className="topology-node" />
      <rect x="480" y="128" width="116" height="68" className="topology-node" />
      <text x="92" y="104" textAnchor="middle" className="topology-symbol active-text">P</text>
      <text x="538" y="58" textAnchor="middle" className="topology-symbol">D1</text>
      <text x="538" y="175" textAnchor="middle" className="topology-symbol">D2</text>
      <text x="332" y="42" textAnchor="middle" className="topology-caption">60%</text>
      <text x="334" y="151" textAnchor="middle" className="topology-caption">30%</text>
      <text x="92" y="169" textAnchor="middle" className="topology-caption">10% UNTRACKED</text>
    </svg>
  );
}

function Capabilities() {
  const [active, setActive] = useState(1);
  const feature = features[active];

  return (
    <section className="capabilities-section section-shell" id="capabilities">
      <SectionHeading
        number="02"
        label="THE ENGINE"
        title="More than a decay curve."
        description="IAEA-sourced nuclides and unit-aware inputs meet an analytical solver that knows when to take the numerically stable route."
      />
      <Reveal className="capability-layout">
        <div className="feature-list" role="tablist" aria-label="Explore pydecay capabilities">
          {features.map((item, index) => (
            <button
              key={item.number}
              type="button"
              role="tab"
              id={`feature-tab-${index}`}
              aria-controls="feature-panel"
              aria-selected={active === index}
              className={`feature-row ${active === index ? "is-active" : ""}`}
              onClick={() => setActive(index)}
            >
              <span className="feature-number">{item.number}</span>
              <span className="feature-text"><strong>{item.title}</strong><small>{item.summary}</small></span>
              <ArrowUpRight size={21} strokeWidth={1.5} />
            </button>
          ))}
        </div>

        <div className="feature-panel" id="feature-panel" role="tabpanel" aria-labelledby={`feature-tab-${active}`}>
          <AnimatePresence mode="wait">
            <motion.div
              key={feature.number}
              className="feature-panel-inner"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.24 }}
            >
              <div className="feature-panel-top"><span>{feature.tag}</span><span>0{active + 1} / 04</span></div>
              <FeatureGraphic type={feature.graphic} />
              <p className="feature-detail">{feature.detail}</p>
              <CodeBlock code={feature.code} label="EXAMPLE / PYTHON" compact className="feature-code" />
            </motion.div>
          </AnimatePresence>
        </div>
      </Reveal>
    </section>
  );
}

const categoryColors: Record<string, string> = {
  "Alkali metal": "#d5a574",
  "Alkaline earth metal": "#c5bb83",
  "Transition metal": "#839ea2",
  "Post-transition metal": "#97a19a",
  Metalloid: "#a5b78c",
  Nonmetal: "#b7a0bd",
  Halogen: "#bda38d",
  "Noble gas": "#b7bba0",
  Lanthanide: "#8cb8b0",
  Actinide: "#afba83",
  Element: "#a0a39c",
};

function PropertyRow({ label, value }: { label: string; value: string }) {
  return <div className="property-row"><span>{label}</span><strong>{value}</strong></div>;
}

function ElementPanel({ element, onTryNuclide }: { element: ElementInfo; onTryNuclide: (id: string) => void }) {
  const featuredId = featuredIsotopes[element.symbol];
  const nuclide = demoNuclides.find((item) => item.id === featuredId);
  const wikiUrl = `https://en.wikipedia.org/wiki/${encodeURIComponent(element.name.replace(/ /g, "_"))}`;

  return (
    <aside className="element-panel" id="element-details" aria-label="Selected element information" aria-live="polite">
      <div className="element-panel-header"><span>ELEMENT FILE / {String(element.number).padStart(3, "0")}</span><span className="panel-crosshair">+</span></div>
      <motion.div
        key={element.number}
        className="element-panel-body"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.16 }}
      >
          <div className="element-identity" style={{ "--identity-color": categoryColors[element.category] ?? "#a0a39c" } as CSSProperties}>
            <strong>{element.symbol}</strong>
            <span>{element.number}</span>
          </div>
          <div className="element-name-block"><h3>{element.name}</h3><span>{element.category.toUpperCase()}</span></div>
          <p className="element-description">Atomic number {element.number} identifies the number of protons in its nucleus. {element.name} sits in period {element.period} of the periodic table.</p>
          <div className="property-list">
            <PropertyRow label="ATOMIC MASS" value={`${element.mass} u`} />
            <PropertyRow label="PERIOD / GROUP" value={`${element.period} / ${element.group ?? "f-block"}`} />
            <PropertyRow label="ELECTRON CONFIG." value={element.configuration} />
            <PropertyRow label="STATE AT ROOM TEMP." value={element.state.charAt(0).toUpperCase() + element.state.slice(1)} />
            <PropertyRow label="ELECTRONEGATIVITY" value={element.electronegativity === null ? "Not available" : String(element.electronegativity)} />
            <PropertyRow label="MELTING POINT" value={element.meltingPoint === null ? "Not available" : `${element.meltingPoint} K`} />
          </div>
          {nuclide && (
            <div className="element-nuclide">
              <span>EXPLORE IN PYDECAY</span>
              <div><strong>{nuclide.id}</strong><small>t1/2 = {nuclide.displayHalfLife}</small></div>
              <button type="button" onClick={() => onTryNuclide(nuclide.id)}>SIMULATE THIS NUCLIDE <ArrowUpRight size={16} /></button>
            </div>
          )}
      </motion.div>
      <a className="wikipedia-link" href={wikiUrl} target="_blank" rel="noreferrer noopener">
        READ ABOUT {element.name.toUpperCase()} ON WIKIPEDIA <ExternalLink size={16} />
      </a>
    </aside>
  );
}

function PeriodicTable({ onTryNuclide }: { onTryNuclide: (id: string) => void }) {
  const [elements, setElements] = useState(fallbackElements);
  const [selectedNumber, setSelectedNumber] = useState(53);
  const [query, setQuery] = useState("");
  const [liveData, setLiveData] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetch("https://api.periodictableofelements.org/elements/", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Element data unavailable");
        return response.json();
      })
      .then((data: unknown) => {
        const enriched = enrichElementsWithApi(data);
        if (enriched) {
          setElements(enriched);
          setLiveData(true);
        }
      })
      .catch(() => {
        // Keep the complete bundled table when the optional data service is offline.
      });
    return () => controller.abort();
  }, []);

  const matchingNumbers = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return null;
    return new Set(
      elements
        .filter((element) => element.name.toLowerCase().includes(term) || element.symbol.toLowerCase().includes(term) || String(element.number) === term)
        .map((element) => element.number),
    );
  }, [elements, query]);

  useEffect(() => {
    if (matchingNumbers?.size) setSelectedNumber(matchingNumbers.values().next().value as number);
  }, [matchingNumbers]);

  const selected = elements.find((element) => element.number === selectedNumber) ?? elements[52];

  function handleElementClick(number: number) {
    setSelectedNumber(number);
    if (window.matchMedia("(max-width: 1180px)").matches) {
      const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
      window.setTimeout(() => document.getElementById("element-details")?.scrollIntoView({ behavior, block: "start" }), 30);
    }
  }

  return (
    <section className="periodic-section section-shell" id="elements">
      <SectionHeading
        number="03"
        label="THE ELEMENTS"
        title="A field guide to matter."
        description="All 118 elements, one place to explore. Hover, focus, or tap an element to open its information file."
      />
      <div className="periodic-toolbar">
        <span><span className="caption-square" /> PERIODIC TABLE / 118 ELEMENTS</span>
        <div className="element-search">
          <Search size={17} aria-hidden="true" />
          <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search an element" aria-label="Search elements by name, symbol, or atomic number" />
          {query && <button type="button" onClick={() => setQuery("")} aria-label="Clear search"><X size={16} /></button>}
        </div>
      </div>
      {matchingNumbers && matchingNumbers.size === 0 && <p className="search-no-results">No element matches "{query}". Try a name, symbol, or atomic number.</p>}
      <div className="periodic-layout">
        <div className="periodic-table-side">
          <div className="periodic-scroll" tabIndex={0} aria-label="Periodic table, scroll horizontally on smaller screens">
            <div className="table-canvas">
              <div className="group-numbers" aria-hidden="true">
                {Array.from({ length: 18 }, (_, index) => <span key={index}>{String(index + 1).padStart(2, "0")}</span>)}
              </div>
              <div className="periodic-grid">
                {elements.map((element) => {
                  const isSelected = selectedNumber === element.number;
                  const dimmed = matchingNumbers !== null && !matchingNumbers.has(element.number);
                  return (
                    <button
                      key={element.number}
                      type="button"
                      className={`element-tile ${isSelected ? "selected" : ""} ${dimmed ? "dimmed" : ""} ${featuredIsotopes[element.symbol] ? "has-demo" : ""}`}
                      style={{ gridColumn: element.column, gridRow: element.row, "--tile-accent": categoryColors[element.category] ?? "#a0a39c" } as CSSProperties}
                      onMouseEnter={() => setSelectedNumber(element.number)}
                      onFocus={() => setSelectedNumber(element.number)}
                      onClick={() => handleElementClick(element.number)}
                      aria-label={`${element.name}, atomic number ${element.number}`}
                      aria-pressed={isSelected}
                      data-element-number={element.number}
                    >
                      <span className="tile-number">{element.number}</span>
                      <strong>{element.symbol}</strong>
                      <span className="tile-indicator" />
                    </button>
                  );
                })}
                <div className="series-placeholder" style={{ gridColumn: 3, gridRow: 6 }} aria-hidden="true">57-71<small>La-Lu</small></div>
                <div className="series-placeholder" style={{ gridColumn: 3, gridRow: 7 }} aria-hidden="true">89-103<small>Ac-Lr</small></div>
                <span className="series-label" style={{ gridColumn: "1 / 3", gridRow: 9 }}>LANTHANIDES</span>
                <span className="series-label" style={{ gridColumn: "1 / 3", gridRow: 10 }}>ACTINIDES</span>
              </div>
            </div>
          </div>
          <div className="table-note">
            <span><i /> FEATURED IN THE PLAYGROUND</span>
            <span>{liveData ? "PROPERTIES: LIVE REFERENCE DATA" : "PROPERTIES: BUNDLED REFERENCE DATA"}</span>
          </div>
        </div>
        <ElementPanel element={selected} onTryNuclide={onTryNuclide} />
      </div>
      <p className="periodic-disclaimer">The table is an element reference. pydecay bundles 47 sourced nuclide records, not every isotope of every element.</p>
    </section>
  );
}

function Verification() {
  const checks = [
    { number: "01", title: "Known values, independently asserted.", detail: "1000 Bq of I-131 becomes 500 Bq after one half-life and 31.25 Bq after five." },
    { number: "02", title: "Solvers checked against each other.", detail: "Bateman and matrix-exponential results agree to 1e-10; near-equal rates stay finite." },
    { number: "03", title: "Another library, another answer.", detail: "Differential tests against radioactivedecay (ICRP-107) fail beyond 1e-3 relative drift." },
  ];

  return (
    <section className="verification-section section-shell" id="verification">
      <SectionHeading
        number="04"
        label="VERIFICATION"
        title="Numbers you can defend."
        description="Scientific software earns trust through reproducible comparisons, not just clean-looking curves."
      />
      <Reveal className="verification-list">
        {checks.map((check) => (
          <div className="verification-row" key={check.number}>
            <span>{check.number} / TEST</span>
            <h3>{check.title}</h3>
            <p>{check.detail}</p>
            <span className="verification-plus">+</span>
          </div>
        ))}
      </Reveal>
    </section>
  );
}

function ClosingCallout() {
  return (
    <section className="closing-section section-shell">
      <Reveal className="closing-inner">
        <span className="section-kicker"><span>05 /</span> START BUILDING</span>
        <h2>Time to make<br /><span>something precise.</span></h2>
        <div className="closing-bottom">
          <p>Install the package, read the guide, and put reliable decay mathematics to work.</p>
          <a href="#/docs" className="button-primary">OPEN DOCUMENTATION <ArrowUpRight size={18} /></a>
        </div>
      </Reveal>
    </section>
  );
}

function HomePage() {
  const [selectedId, setSelectedId] = useState("I-131");

  function tryNuclide(id: string) {
    setSelectedId(id);
    window.location.hash = "#playground";
    const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
    document.getElementById("playground")?.scrollIntoView({ behavior });
  }

  return (
    <main>
      <Hero />
      <Playground selectedId={selectedId} onSelect={setSelectedId} />
      <Capabilities />
      <PeriodicTable onTryNuclide={tryNuclide} />
      <Verification />
      <ClosingCallout />
    </main>
  );
}

const quickstartCode = `from pydecay import Nuclide, DecayChain, decayed_activity, remaining_fraction\n\n# 1000 Bq of I-131 after one half-life -> 500 Bq\ni131 = Nuclide.load("I-131")\na = decayed_activity(A0=1000.0, half_life=i131.half_life, time=i131.half_life)\n\n# Five half-lives leave 3.125%\nf = remaining_fraction(half_life=i131.half_life, time=5 * i131.half_life)`;

const chainCode = `from pydecay import DecayChain\n\n# Parent -> stable; plain floats or pint-aware time\nchain = DecayChain([0.693, 0.0], names=["parent", "stable"])\nprint(chain.at(t="1 days", n0={"parent": 1e6, "stable": 0.0}))`;

const branchingCode = `from pydecay import DecayChain\n\nb = DecayChain.branching(\n    parent="P",\n    branches={"D1": 0.6, "D2": 0.3},\n    lambdas={"P": 0.7, "D1": 1e-5, "D2": 2e-5},\n)`;

const docsNavigation = [
  { id: "installation", label: "Installation" },
  { id: "quickstart", label: "Quickstart" },
  { id: "single-isotope", label: "Single isotope" },
  { id: "decay-chains", label: "Decay chains" },
  { id: "branching", label: "Branching" },
  { id: "solver", label: "Solver strategy" },
  { id: "data-units", label: "Data & units" },
  { id: "verification", label: "Verification" },
];

function DocsSection({ id, number, title, children }: { id: string; number: string; title: string; children: ReactNode }) {
  return (
    <section className="docs-section" id={id}>
      <span className="docs-section-number">{number} / GUIDE</span>
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function DocsPage({ hash }: { hash: string }) {
  const activeSection = hash.split("/")[2] || "installation";

  return (
    <main className="docs-page">
      <div className="docs-masthead section-shell">
        <span className="section-kicker"><span>PYDECAY /</span> FIELD MANUAL</span>
        <h1>Documentation<span>.</span></h1>
        <p>Everything you need to model radioactive decay with confidence, from your first half-life to a branching chain.</p>
        <div className="docs-masthead-meta"><span>PYTHON 3.10+</span><span>MIT LICENSE</span><span>VERSION 0.1.0</span></div>
      </div>

      <div className="docs-layout section-shell">
        <aside className="docs-sidebar" aria-label="Documentation sections">
          <span className="docs-sidebar-label">CONTENTS / 08</span>
          <nav>
            {docsNavigation.map((item, index) => (
              <a key={item.id} href={`#/docs/${item.id}`} className={activeSection === item.id ? "current" : ""}>
                <span>{String(index + 1).padStart(2, "0")}</span>{item.label}
              </a>
            ))}
          </nav>
          <a className="docs-sidebar-source" href={GITHUB_URL} target="_blank" rel="noreferrer noopener">VIEW SOURCE <ArrowUpRight size={15} /></a>
        </aside>

        <article className="docs-article">
          <DocsSection id="installation" number="01" title="Installation">
            <p>Install pydecay from PyPI in a Python 3.10 or newer environment. NumPy, SciPy, and Pint are installed as runtime dependencies.</p>
            <CodeBlock code="pip install pydecay" label="TERMINAL" />
            <div className="docs-inline-note"><span>REQUIRES</span><strong>Python &gt;= 3.10</strong><span>DEPENDS ON</span><strong>numpy / scipy / pint</strong></div>
          </DocsSection>

          <DocsSection id="quickstart" number="02" title="Quickstart">
            <p>Load a bundled nuclide, compute its activity after one half-life, and find the dimensionless fraction remaining after five.</p>
            <CodeBlock code={quickstartCode} />
            <p className="docs-small-result"><span>EXPECTED RESULT</span> 500 Bq after one half-life; 0.03125 of the initial amount after five.</p>
          </DocsSection>

          <DocsSection id="single-isotope" number="03" title="Single-isotope decay">
            <p>For an isolated isotope, the number of atoms falls exponentially. Activity is the decay constant multiplied by the number of undecayed atoms.</p>
            <div className="docs-equation">
              <span>THE MODEL</span>
              <div>N(t) = N<sub>0</sub>e<sup>-&lambda;t</sup></div>
              <small>&lambda; = ln(2) / t<sub>1/2</sub> &nbsp; &middot; &nbsp; A(t) = &lambda;N(t)</small>
            </div>
            <p><code>decayed_activity</code> returns activity for the supplied starting activity, half-life, and elapsed time. <code>remaining_fraction</code> returns the unitless surviving fraction.</p>
            <CodeBlock code={`from pydecay import Nuclide, decayed_activity, remaining_fraction\n\ni131 = Nuclide.load("I-131")\nactivity = decayed_activity(A0=1000.0, half_life=i131.half_life, time=i131.half_life)\nfraction = remaining_fraction(half_life=i131.half_life, time=5 * i131.half_life)`} />
          </DocsSection>

          <DocsSection id="decay-chains" number="04" title="Linear decay chains">
            <p>Use <code>DecayChain</code> to evolve populations through a sequence of parent and daughter nuclides. A zero decay constant represents a stable endpoint.</p>
            <CodeBlock code={chainCode} />
            <p>When decay constants are well separated, the solver uses the Bateman closed form. Time inputs can be plain values or Pint-style strings such as <code>"1 days"</code>.</p>
          </DocsSection>

          <DocsSection id="branching" number="05" title="Branching topologies">
            <p>Split a parent into multiple daughters with explicitly defined branch fractions and decay constants.</p>
            <CodeBlock code={branchingCode} />
            <div className="docs-rule"><span>BRANCH RULE</span><p>Fractions must add up to no more than 1. In this example, the remaining 10% leaves the tracked system as an untracked sink.</p></div>
          </DocsSection>

          <DocsSection id="solver" number="06" title="Solver strategy">
            <p>pydecay switches methods where the mathematics demands it. The goal is a finite, stable answer rather than forcing a fragile closed form.</p>
            <div className="docs-strategy">
              <div><span>01 / BATEMAN</span><strong>Well-separated linear chains</strong><p>Use the analytical closed form when decay constants are safely distinct.</p></div>
              <div><span>02 / MATRIX EXPONENTIAL</span><strong>Numerically delicate cases</strong><p>Use <code>scipy.linalg.expm</code> for nearly equal rates, branching, or nonzero daughter initial populations.</p></div>
            </div>
            <p>Regression tests keep the near-degenerate 0.6931 / 0.6932 case finite and compare the two solvers to 1e-10 where both apply.</p>
          </DocsSection>

          <DocsSection id="data-units" number="07" title="Nuclide data & units">
            <p>The package bundles 47 nuclides with per-record source and fetch date from the IAEA Live Chart of Nuclides. This site&apos;s 118-element table is a separate reference, not a promise that every isotope is bundled.</p>
            <div className="docs-strategy units-strategy">
              <div><span>INTERNAL REPRESENTATION</span><strong>Seconds / atoms / Bq</strong><p>Calculations stay in consistent base quantities.</p></div>
              <div><span>AT THE BOUNDARY</span><strong>Bq &harr; Ci / atoms &harr; grams</strong><p>Unit conversions are available at the edges of the calculation.</p></div>
            </div>
            <p>See the <a href="https://www.iaea.org/resources/databases/livechart-of-nuclides" target="_blank" rel="noreferrer noopener">IAEA Live Chart <ArrowUpRight size={14} /></a> for the underlying nuclide reference.</p>
          </DocsSection>

          <DocsSection id="verification" number="08" title="Verification & next steps">
            <p>Worked examples and solver comparisons are part of the project tests. Differential checks against radioactivedecay (ICRP-107) report drift and fail past 1e-3 relative difference.</p>
            <div className="docs-check-list">
              <div><span>01</span><strong>Known I-131 values</strong><code>tests/test_known_values.py</code></div>
              <div><span>02</span><strong>Bateman / expm agreement</strong><code>tests/test_solver.py</code></div>
              <div><span>03</span><strong>External differential check</strong><code>tests/test_crosscheck.py</code></div>
            </div>
            <p>For contributors, the quality gates include at least 90% test coverage, static checks, and a strict documentation build.</p>
            <CodeBlock code={`pytest\nruff check src tests\nmypy src\nmkdocs build --strict`} label="CONTRIBUTOR CHECKS" />
            <p>For derivations and solver-dispatch diagrams, continue into the project&apos;s <a href={`${GITHUB_URL}/tree/main/docs`} target="_blank" rel="noreferrer noopener">full docs source <ArrowUpRight size={14} /></a>.</p>
            <div className="docs-final-links">
              <a href={GITHUB_URL} target="_blank" rel="noreferrer noopener">EXPLORE GITHUB <ArrowUpRight size={16} /></a>
              <a href={PYPI_URL} target="_blank" rel="noreferrer noopener">VIEW ON PYPI <ArrowUpRight size={16} /></a>
            </div>
          </DocsSection>
        </article>
      </div>
    </main>
  );
}

function Footer() {
  return (
    <footer className="site-footer section-shell">
      <div className="footer-top">
        <a href="#/" className="footer-brand">pydecay<span>.</span></a>
        <p>Scientific decay mathematics,<br />made usable.</p>
        <div className="footer-links">
          <a href="#/docs">DOCUMENTATION <ArrowUpRight size={15} /></a>
          <a href={GITHUB_URL} target="_blank" rel="noreferrer noopener">GITHUB <ArrowUpRight size={15} /></a>
          <a href={PYPI_URL} target="_blank" rel="noreferrer noopener">PYPI <ArrowUpRight size={15} /></a>
        </div>
      </div>
      <div className="footer-bottom">
        <span>BUILT BY DANIEL DESHMUKH / MIT LICENSE</span>
        <span>ELEMENT REFERENCE: <a href="https://periodictableofelements.org" target="_blank" rel="noreferrer noopener">PERIODICTABLEOFELEMENTS.ORG</a> + <a href="https://github.com/andrejewski/periodic-table" target="_blank" rel="noreferrer noopener">PERIODIC-TABLE</a></span>
        <span>&copy; PYDECAY</span>
      </div>
    </footer>
  );
}

export default function App() {
  const [hash, setHash] = useState(() => window.location.hash || "#/");
  const isDocs = hash.startsWith("#/docs");

  useEffect(() => {
    document.title = isDocs ? "Documentation | pydecay" : "pydecay | Radioactive Decay Mathematics for Python";
  }, [isDocs]);

  useEffect(() => {
    const onHashChange = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      const target = hash.startsWith("#/docs/") ? hash.split("/")[2] : hash.startsWith("#") && !hash.startsWith("#/") ? hash.slice(1) : null;
      const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
      if (target) document.getElementById(target)?.scrollIntoView({ behavior, block: "start" });
      else window.scrollTo({ top: 0, behavior: "auto" });
    }, 30);
    return () => window.clearTimeout(timeout);
  }, [hash, isDocs]);

  return (
    <MotionConfig reducedMotion="user">
      <SiteHeader hash={hash} />
      {isDocs ? <DocsPage hash={hash} /> : <HomePage />}
      <Footer />
    </MotionConfig>
  );
}
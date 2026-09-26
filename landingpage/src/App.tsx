import {
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
  type MouseEvent,
  type ReactNode,
} from "react";
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
import {
  activityLiteral,
  AVOGADRO_PER_MOL,
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
  UNIT_FACTS,
} from "./utils/calculations";
import {
  doseCoefficientFor,
  doseRate,
  engineeringParts,
  formatEngineering,
  type DoseQuantity,
} from "./utils/dose";
import { hvlSlab, muFromMaterial, transmitSlab, tvlSlab } from "./utils/shielding";
import { doseCoefficientRows, omittedPhotonNuclides } from "./data/doseCoefficients";
import {
  shieldingMaterialOrder,
  shieldingMaterials,
  type ShieldingMaterialId,
} from "./data/shieldingTables";

const GITHUB_URL = "https://github.com/DanielDeshmukh/pydecay";
const PYPI_URL = "https://pypi.org/project/pydecay/";
// Mirrors --accent in index.css; SVG presentation attributes can't read CSS variables.
const ACCENT = "#55b0f3";

function currentPath(): string {
  const path = window.location.pathname.replace(/\/+$/, "");
  return path === "" ? "/" : path;
}

function navigate(to: string) {
  const next = new URL(to, window.location.origin);
  if (next.pathname !== window.location.pathname) {
    window.history.pushState(null, "", next.pathname);
    window.dispatchEvent(new PopStateEvent("popstate"));
  } else {
    window.scrollTo({ top: 0, behavior: "auto" });
  }
}

function scrollToId(id: string) {
  const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ? "auto"
    : "smooth";
  window.setTimeout(
    () => document.getElementById(id)?.scrollIntoView({ behavior, block: "start" }),
    30,
  );
}

function useInternalNav() {
  return (to: string) => (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(to);
  };
}

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

function SiteHeader({ path }: { path: string }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const nav = useInternalNav();
  const isDocs = path === "/docs" || path.startsWith("/docs/");
  const links = [
    { label: "OVERVIEW", href: "/", active: path === "/" },
    { label: "PLAYGROUND", href: "/playground", active: path === "/playground" },
    { label: "ELEMENTS", href: "/elements", active: path === "/elements" },
    { label: "DOCS", href: "/docs", active: isDocs },
  ];

  return (
    <header className="site-header">
      <div className="header-inner">
        <a
          href="/"
          className="brand-link"
          onClick={(event) => {
            nav("/")(event);
            setMenuOpen(false);
          }}
          aria-label="pydecay home"
        >
          <LogoMark />
          <span>
            pydecay<span className="brand-period">.</span>
          </span>
        </a>

        <nav className="desktop-nav" aria-label="Main navigation">
          {links.map((link) => (
            <a
              className={link.active ? "nav-active" : ""}
              href={link.href}
              key={link.label}
              onClick={nav(link.href)}
            >
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
            <a
              href={link.href}
              key={link.label}
              onClick={(event) => {
                nav(link.href)(event);
                setMenuOpen(false);
              }}
            >
              {link.label}
              <ArrowUpRight size={18} />
            </a>
          ))}
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer noopener"
            onClick={() => setMenuOpen(false)}
          >
            GITHUB
            <ArrowUpRight size={18} />
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

function HeroPlot() {
  const mainPath = decayPath(570, 140, 650, 900, 5);

  return (
    <svg
      className="hero-plot"
      viewBox="0 0 1440 760"
      preserveAspectRatio="xMidYMid slice"
      role="img"
      aria-label="A plotted exponential radioactive decay curve over five half-lives"
    >
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
        {[570, 750, 930, 1110, 1290, 1470].map((x) => (
          <line key={`v-${x}`} x1={x} x2={x} y1="115" y2="650" />
        ))}
        {[140, 242, 344, 446, 548, 650].map((y) => (
          <line key={`h-${y}`} x1="570" x2="1470" y1={y} y2={y} />
        ))}
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
      <path
        d="M750 395V650M570 395H750"
        stroke={ACCENT}
        strokeWidth="1"
        strokeDasharray="5 7"
        opacity="0.55"
      />
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
        <text x="592" y="102">
          ACTIVITY / A(t)
        </text>
        <text x="1400" y="702" textAnchor="end">
          TIME / HALF-LIVES
        </text>
        <text x="750" y="680" textAnchor="middle">
          1
        </text>
        <text x="930" y="680" textAnchor="middle">
          2
        </text>
        <text x="1110" y="680" textAnchor="middle">
          3
        </text>
        <text x="1290" y="680" textAnchor="middle">
          4
        </text>
        <text x="715" y="375">
          t1/2
        </text>
      </g>
    </svg>
  );
}

function Hero() {
  const nav = useInternalNav();

  return (
    <section className="hero" id="top">
      <HeroPlot />
      <div className="hero-plot-shade" />
      <div className="hero-copy page-gutter">
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.75, delay: 0.1 }}
        >
          <span className="hero-overline">
            <span className="live-square" /> OPEN-SOURCE SCIENTIFIC PYTHON
          </span>
          <h1>
            pydecay<span>.</span>
          </h1>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.75, delay: 0.32 }}
        >
          <h2>Model what remains.</h2>
          <p>
            Radioactive decay mathematics for Python. From a single isotope to branching chains,
            with dose rates and shielding built in.
          </p>
          <div className="hero-actions">
            <a href="/docs" className="button-primary" onClick={nav("/docs")}>
              READ THE DOCS <ArrowUpRight size={18} />
            </a>
            <a
              href="/playground"
              className="text-link"
              onClick={(event) => {
                event.preventDefault();
                navigate("/playground");
                scrollToId("playground");
              }}
            >
              EXPLORE THE PLAYGROUND <ArrowRight size={17} />
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function SectionHeading({
  number,
  label,
  title,
  description,
}: {
  number: string;
  label: string;
  title: string;
  description: string;
}) {
  return (
    <Reveal className="section-heading">
      <div className="section-heading-left">
        <span className="section-kicker">
          <span>{number} /</span> {label}
        </span>
        <h2>{title}</h2>
      </div>
      <p>{description}</p>
    </Reveal>
  );
}

type PlaygroundMode = "decay" | "dose" | "shielding";

const playgroundModes: Array<{ id: PlaygroundMode; label: string }> = [
  { id: "decay", label: "DECAY" },
  { id: "dose", label: "DOSE" },
  { id: "shielding", label: "SHIELDING" },
];

/** Label for an evenly spaced log10 axis tick (0.1, 0.40, 1.6, 6.3, 25, 100). */
function logTickLabel(decadeExponent: number): string {
  const value = 10 ** decadeExponent;
  return value >= 100 ? "100" : value.toPrecision(2);
}

function DecayPanel({
  selectedId,
  onSelect,
}: {
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  const [activityInput, setActivityInput] = useState("1000");
  const [halfLives, setHalfLives] = useState(1);
  const nuclide = demoNuclides.find((item) => item.id === selectedId) ?? demoNuclides[0];
  const initialActivity = parseActivityInput(activityInput);
  const initialLiteral = activityLiteral(initialActivity);
  const remaining = remainingFraction(halfLives);
  const activity = decayedActivity(initialActivity, halfLives);
  const elapsed = elapsedTime(halfLives, nuclide.halfLifeDays, nuclide.daysPerUnit);
  const chartPath = decayPath(CHART.left, CHART.top, CHART.bottom, CHART.width, CHART.maxHalfLives);
  const markerCX = markerX(halfLives);
  const markerCY = markerY(remaining);
  const code = `from pydecay import Nuclide, decayed_activity\n\nnuclide = Nuclide.load("${nuclide.id}")\nactivity = decayed_activity(\n    A0=${initialLiteral},\n    half_life=nuclide.half_life,\n    time=${halfLives.toFixed(2)} * nuclide.half_life,\n)  # ${formatActivity(activity)} Bq`;

  return (
    <Reveal className="workbench">
      <div className="workbench-controls">
        <div className="workbench-caption">
          <span className="caption-square" /> INPUT PARAMETERS <span>01 / 03</span>
        </div>

        <label className="field-label" htmlFor="nuclide-select">
          NUCLIDE
        </label>
        <div className="select-wrap">
          <select
            id="nuclide-select"
            value={nuclide.id}
            onChange={(event) => onSelect(event.target.value)}
          >
            {demoNuclides.map((item) => (
              <option key={item.id} value={item.id}>
                {item.id} / {item.element}
              </option>
            ))}
          </select>
          <ChevronDown size={17} aria-hidden="true" />
        </div>
        <p className="field-hint">Half-life: {nuclide.displayHalfLife}</p>

        <label className="field-label activity-label" htmlFor="initial-activity">
          INITIAL ACTIVITY
        </label>
        <div className="number-wrap">
          <input
            id="initial-activity"
            type="number"
            min="1"
            step="any"
            value={activityInput}
            onChange={(event) => setActivityInput(event.target.value)}
            onBlur={() => {
              if (!Number.isFinite(Number(activityInput)) || Number(activityInput) <= 0)
                setActivityInput("1000");
            }}
          />
          <span>Bq</span>
        </div>

        <div className="time-label-row">
          <label className="field-label" htmlFor="time-slider">
            TIME ELAPSED
          </label>
          <span>
            {elapsed.toFixed(2)} {nuclide.timeUnit}
          </span>
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
          aria-valuetext={`${elapsed.toFixed(2)} ${nuclide.timeUnit}, ${halfLives.toFixed(2)} half-lives`}
        />
        <div className="range-ends">
          <span>0</span>
          <span>5 HALF-LIVES</span>
        </div>

        <div className="result-readout" aria-live="polite">
          <span>ACTIVITY REMAINING</span>
          <div>
            {formatActivity(activity)} <small>Bq</small>
          </div>
          <p>{percentRemaining(remaining)}% of the initial activity remains</p>
        </div>
      </div>

      <div className="workbench-output">
        <div className="output-topline">
          <span>
            DECAY CURVE <i /> {nuclide.id}
          </span>
          <span>
            A(t) = A0 * 2<sup>-t / t1/2</sup>
          </span>
        </div>
        <div className="chart-wrap">
          <svg
            viewBox="0 0 760 410"
            preserveAspectRatio="xMidYMid meet"
            role="img"
            aria-label={`${nuclide.id} decay curve, ${formatActivity(activity)} becquerels remaining after ${elapsed.toFixed(2)} ${nuclide.timeUnit}`}
          >
            <defs>
              <linearGradient id="workbench-area" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={ACCENT} stopOpacity="0.14" />
                <stop offset="100%" stopColor={ACCENT} stopOpacity="0" />
              </linearGradient>
            </defs>
            {[58, 126, 194, 262, 330].map((y, index) => (
              <g key={y}>
                <line className="chart-grid-line" x1="62" x2="712" y1={y} y2={y} />
                <text className="chart-tick" x="48" y={y + 4} textAnchor="end">
                  {formatAxis(initialActivity * (1 - index / 4))}
                </text>
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
              animate={{ x1: markerCX, x2: markerCX }}
              transition={{ duration: 0.4, ease: "easeOut" }}
            />
            <motion.circle
              r="7"
              fill={ACCENT}
              stroke="#151617"
              strokeWidth="3"
              initial={false}
              animate={{ cx: markerCX, cy: markerCY }}
              transition={{ duration: 0.4, ease: "easeOut" }}
            />
            <text className="chart-axis-title" x="62" y="24">
              ACTIVITY / Bq
            </text>
            <text className="chart-axis-title" x="712" y="400" textAnchor="end">
              TIME / {nuclide.timeUnit.toUpperCase()}
            </text>
          </svg>
        </div>
        <CodeBlock code={code} label="GENERATED PYTHON" compact className="workbench-code" />
      </div>
    </Reveal>
  );
}

function DosePanel() {
  const [nuclideId, setNuclideId] = useState("Co-60");
  const [activityInput, setActivityInput] = useState("1e6");
  const [logDistance, setLogDistance] = useState(0);
  const [quantity, setQuantity] = useState<DoseQuantity>("kerma");

  const parsedActivity = Number(activityInput);
  const activity = Number.isFinite(parsedActivity) && parsedActivity > 0 ? parsedActivity : 1e6;
  const distance = 10 ** logDistance;
  const rate = doseRate(activity, nuclideId, distance, quantity);
  const gamma = doseCoefficientFor(nuclideId);
  const rateParts = engineeringParts(rate ?? 0);
  const unit = quantity === "ambient" ? "Sv/h" : "Gy/h";
  const markerX = 62 + ((logDistance + 1) / 3) * 650;
  const markerY = 58 + ((logDistance + 1) / 3) * 270;
  const code = `from pydecay import dose_rate\n\nrate = dose_rate(${activityLiteral(activity)}, "${nuclideId}", r=${distance.toFixed(2)}, quantity="${quantity}")\nprint(rate)  # ${
    rate === null ? "DoseDataError" : `${rateParts.mantissa} ${rateParts.suffix}${unit}`
  }`;

  return (
    <Reveal className="workbench">
      <div className="workbench-controls">
        <div className="workbench-caption">
          <span className="caption-square" /> DOSE PARAMETERS <span>02 / 03</span>
        </div>

        <label className="field-label" htmlFor="dose-nuclide-select">
          SOURCE NUCLIDE
        </label>
        <div className="select-wrap">
          <select
            id="dose-nuclide-select"
            value={nuclideId}
            onChange={(event) => setNuclideId(event.target.value)}
          >
            {doseCoefficientRows.map((row) => (
              <option key={row.id} value={row.id}>
                {row.id}
              </option>
            ))}
          </select>
          <ChevronDown size={17} aria-hidden="true" />
        </div>
        <p className="field-hint">
          Γ = {gamma === null ? "—" : gamma} R·cm²/mCi/h - bundled exposure-rate constant
        </p>
        <p className="field-hint">
          Photon-free ({Object.keys(omittedPhotonNuclides).join(", ")}) raise DoseDataError.
        </p>

        <label className="field-label activity-label" htmlFor="dose-activity">
          ACTIVITY
        </label>
        <div className="number-wrap">
          <input
            id="dose-activity"
            type="number"
            min="1"
            step="any"
            value={activityInput}
            onChange={(event) => setActivityInput(event.target.value)}
            onBlur={() => {
              if (!(Number.isFinite(Number(activityInput)) && Number(activityInput) > 0)) {
                setActivityInput("1e6");
              }
            }}
          />
          <span>Bq</span>
        </div>

        <div className="time-label-row">
          <label className="field-label" htmlFor="dose-distance">
            DISTANCE
          </label>
          <span>{distance.toFixed(2)} m</span>
        </div>
        <input
          className="time-slider"
          id="dose-distance"
          type="range"
          min="-1"
          max="2"
          step="0.01"
          value={logDistance}
          style={{ "--slider-progress": `${((logDistance + 1) / 3) * 100}%` } as CSSProperties}
          onChange={(event) => setLogDistance(Number(event.target.value))}
          aria-valuetext={`${distance.toFixed(2)} metres`}
        />
        <div className="range-ends">
          <span>0.1 m</span>
          <span>100 m</span>
        </div>

        <span className="field-label">QUANTITY</span>
        <div className="quantity-toggle" role="group" aria-label="Dose quantity">
          <button
            type="button"
            aria-pressed={quantity === "kerma"}
            className={quantity === "kerma" ? "is-active" : ""}
            onClick={() => setQuantity("kerma")}
          >
            KERMA - Gy/h
          </button>
          <button
            type="button"
            aria-pressed={quantity === "ambient"}
            className={quantity === "ambient" ? "is-active" : ""}
            onClick={() => setQuantity("ambient")}
          >
            AMBIENT - Sv/h
          </button>
        </div>

        <div className="result-readout" aria-live="polite">
          <span>{quantity === "ambient" ? "AMBIENT DOSE RATE" : "AIR KERMA RATE"}</span>
          <div>
            {rate === null ? "—" : rateParts.mantissa}{" "}
            <small>
              {rate === null ? "" : rateParts.suffix}
              {unit}
            </small>
          </div>
          <p>
            {rate === null
              ? `No photon coefficients for ${nuclideId} - pydecay raises DoseDataError.`
              : `${activityLiteral(activity)} Bq at ${distance.toFixed(2)} m - inverse-square point source`}
          </p>
        </div>
      </div>

      <div className="workbench-output">
        <div className="output-topline">
          <span>
            DOSE RATE <i /> {nuclideId}
          </span>
          <span>Ξ(r) = Γ · A / r²</span>
        </div>
        <div className="chart-wrap">
          <svg
            viewBox="0 0 760 410"
            preserveAspectRatio="xMidYMid meet"
            role="img"
            aria-label={`Inverse-square dose rate curve for ${nuclideId}, marker at ${distance.toFixed(2)} metres`}
          >
            {[0, 1, 2, 3, 4, 5, 6].map((step) => {
              const y = 58 + step * 45;
              return (
                <g key={`db-${step}`}>
                  <line className="chart-grid-line" x1="62" x2="712" y1={y} y2={y} />
                  <text className="chart-tick" x="48" y={y + 4} textAnchor="end">
                    {step === 0 ? "0" : `-${step * 10}`} dB
                  </text>
                </g>
              );
            })}
            {[-1, -0.4, 0.2, 0.8, 1.4, 2].map((decade) => {
              const x = 62 + ((decade + 1) / 3) * 650;
              return (
                <g key={decade}>
                  <line className="chart-grid-line vertical" x1={x} x2={x} y1="58" y2="328" />
                  <text className="chart-tick" x={x} y="361" textAnchor="middle">
                    {logTickLabel(decade)}
                  </text>
                </g>
              );
            })}
            <line x1="62" y1="58" x2="712" y2="328" stroke="#4a667d" strokeWidth="2" />
            <motion.line
              className="chart-marker-line"
              y1="58"
              y2="328"
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
            <text className="chart-axis-title" x="62" y="24">
              RELATIVE RATE / dB
            </text>
            <text className="chart-axis-title" x="712" y="400" textAnchor="end">
              DISTANCE / m (log)
            </text>
          </svg>
        </div>
        <CodeBlock code={code} label="GENERATED PYTHON" compact className="workbench-code" />
      </div>
    </Reveal>
  );
}

function ShieldingPanel() {
  const [materialId, setMaterialId] = useState<ShieldingMaterialId>("lead");
  const [logEnergy, setLogEnergy] = useState(Math.log10(1.25));
  const [thicknessMm, setThicknessMm] = useState(10);

  const energy = 10 ** logEnergy;
  const energyLabel = Number(energy.toPrecision(3));
  const energySpan = Math.log10(20) + 2;
  const thicknessM = thicknessMm / 1000;
  const mu = muFromMaterial(materialId, energy);
  const half = hvlSlab(materialId, energy);
  const tenth = tvlSlab(materialId, energy);
  const transmitted = transmitSlab(1, materialId, thicknessM, energy);
  const material = shieldingMaterials[materialId];
  const percent = transmitted === null ? 0 : transmitted * 100;
  const percentLabel = percent >= 0.01 ? percent.toFixed(3) : percent.toExponential(1);
  const code = `from pydecay import hvl_slab, transmit_slab\n\nprint(hvl_slab("${materialId}", ${energyLabel}))  # ${
    half === null ? "?" : `${(half * 1000).toFixed(2)} mm`
  }\nprint(transmit_slab(1.0, "${materialId}", ${thicknessM.toFixed(4)}, ${energyLabel}))  # ${percentLabel} %`;

  return (
    <Reveal className="workbench">
      <div className="workbench-controls">
        <div className="workbench-caption">
          <span className="caption-square" /> SHIELDING PARAMETERS <span>03 / 03</span>
        </div>

        <label className="field-label" htmlFor="shield-material-select">
          SHIELD MATERIAL
        </label>
        <div className="select-wrap">
          <select
            id="shield-material-select"
            value={materialId}
            onChange={(event) => setMaterialId(event.target.value as ShieldingMaterialId)}
          >
            {shieldingMaterialOrder.map((id) => (
              <option key={id} value={id}>
                {shieldingMaterials[id].label}
              </option>
            ))}
          </select>
          <ChevronDown size={17} aria-hidden="true" />
        </div>
        <p className="field-hint">
          ρ = {material.densityGcm3} g/cm³ - NIST XCOM, 45 log-spaced energies
        </p>

        <div className="time-label-row">
          <label className="field-label" htmlFor="shield-energy">
            PHOTON ENERGY
          </label>
          <span>{energyLabel} MeV</span>
        </div>
        <input
          className="time-slider"
          id="shield-energy"
          type="range"
          min="-2"
          max={Math.log10(20)}
          step="0.001"
          value={logEnergy}
          style={
            {
              "--slider-progress": `${((logEnergy + 2) / energySpan) * 100}%`,
            } as CSSProperties
          }
          onChange={(event) => setLogEnergy(Number(event.target.value))}
          aria-valuetext={`${energyLabel} megaelectronvolts`}
        />
        <div className="range-ends">
          <span>0.01 MeV</span>
          <span>20 MeV</span>
        </div>

        <div className="time-label-row">
          <label className="field-label" htmlFor="shield-thickness">
            THICKNESS
          </label>
          <span>{thicknessMm.toFixed(1)} mm</span>
        </div>
        <input
          className="time-slider"
          id="shield-thickness"
          type="range"
          min="0"
          max="100"
          step="0.5"
          value={thicknessMm}
          style={{ "--slider-progress": `${thicknessMm}%` } as CSSProperties}
          onChange={(event) => setThicknessMm(Number(event.target.value))}
          aria-valuetext={`${thicknessMm.toFixed(1)} millimetres`}
        />
        <div className="range-ends">
          <span>0 mm</span>
          <span>100 mm</span>
        </div>

        <div className="result-readout" aria-live="polite">
          <span>TRANSMITTED INTENSITY</span>
          <div>
            {transmitted === null ? "—" : percentLabel} <small>%</small>
          </div>
          <p>
            {mu === null || half === null || tenth === null
              ? "Energy outside the bundled 0.01-20 MeV table."
              : `μ = ${formatEngineering(mu)} m⁻¹ · HVL = ${formatEngineering(half * 1000, 2)} mm · TVL = ${formatEngineering(tenth * 1000, 2)} mm`}
          </p>
        </div>
      </div>

      <div className="workbench-output">
        <div className="output-topline">
          <span>
            ATTENUATION <i /> {material.label.toUpperCase()}
          </span>
          <span>I = I0 · exp(−μ · x)</span>
        </div>
        <div
          className="shield-bars"
          role="img"
          aria-label={`Transmission through ${material.label}: ${percentLabel} percent of incident intensity`}
        >
          <div className="shield-bar-row">
            <span className="shield-bar-name">INCIDENT I0</span>
            <div className="shield-bar-track">
              <div className="shield-bar-fill is-incident" />
            </div>
            <strong>100%</strong>
          </div>
          <div className="shield-bar-row">
            <span className="shield-bar-name">TRANSMITTED I</span>
            <div className="shield-bar-track">
              <motion.div
                className="shield-bar-fill is-transmitted"
                initial={false}
                animate={{ width: `${Math.max(percent, 0)}%` }}
                transition={{ duration: 0.4, ease: "easeOut" }}
              />
            </div>
            <strong>{percentLabel}%</strong>
          </div>
          <p className="shield-bar-caption">
            {thicknessMm.toFixed(1)} mm {material.label} at {energyLabel} MeV - narrow-beam, no
            buildup
          </p>
        </div>
        <CodeBlock code={code} label="GENERATED PYTHON" compact className="workbench-code" />
      </div>
    </Reveal>
  );
}

function Playground({
  selectedId,
  onSelect,
}: {
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  const [mode, setMode] = useState<PlaygroundMode>("decay");

  return (
    <section className="playground-section section-shell" id="playground">
      <SectionHeading
        number="01"
        label="THE PLAYGROUND"
        title="See time do its work."
        description="Three live models in your browser: decay curves, point-source dose rates, and narrow-beam shielding - each one generating the exact pydecay call to run in Python."
      />
      <div className="playground-mode-tabs" role="tablist" aria-label="Playground mode">
        {playgroundModes.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={mode === item.id}
            className={mode === item.id ? "is-active" : ""}
            onClick={() => setMode(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {mode === "decay" && <DecayPanel selectedId={selectedId} onSelect={onSelect} />}
      {mode === "dose" && <DosePanel />}
      {mode === "shielding" && <ShieldingPanel />}
      <p className="workbench-footnote">
        Preview calculated in your browser. Run the generated code with pydecay for your Python
        workflow.
      </p>
    </section>
  );
}

type ConverterMode = "activity" | "mass" | "time" | "decay";

const converterModes: Array<{ id: ConverterMode; label: string; formula: string }> = [
  { id: "activity", label: "Bq ↔ Ci", formula: "Ci = Bq / 3.7×10¹⁰" },
  { id: "mass", label: "atoms ↔ g", formula: "g = N · u / N_A" },
  { id: "time", label: "time → s", formula: "s = value × unit" },
  { id: "decay", label: "T½ → λ, τ", formula: "λ = ln2 / T½ · τ = 1/λ" },
];

function UnitConverter() {
  const [mode, setMode] = useState<ConverterMode>("activity");
  const [activityInput, setActivityInput] = useState("3.7e10");
  const [massGInput, setMassGInput] = useState("1.0");
  const [massUInput, setMassUInput] = useState("130.9061");
  const [atomsInput, setAtomsInput] = useState("6.02214076e23");
  const [timeInput, setTimeInput] = useState("8.02 days");
  const [halfLifeDaysInput, setHalfLifeDaysInput] = useState("8.0228");

  function parsePositive(raw: string, fallback: number): number {
    const n = Number(raw);
    return Number.isFinite(n) && n > 0 ? n : fallback;
  }

  const activityBq = parsePositive(activityInput, 3.7e10);
  const massG = parsePositive(massGInput, 1);
  const massU = parsePositive(massUInput, 130.9061);
  const atomsN = parsePositive(atomsInput, AVOGADRO_PER_MOL);
  const halfLifeDays = parsePositive(halfLifeDaysInput, 8.0228);

  let primaryLabel = "ACTIVITY";
  let primaryValue = "";
  let primaryUnit = "";
  let secondaryLabel = "";
  let secondaryValue = "";
  let secondaryUnit = "";
  let explanation = "";
  let code = "";
  let error: string | null = null;

  if (mode === "activity") {
    const ci = bqToCi(activityBq);
    primaryLabel = "BECQUERELS";
    primaryValue = formatConverter(activityBq);
    primaryUnit = "Bq";
    secondaryLabel = "CURIES";
    secondaryValue = formatConverter(ci);
    secondaryUnit = "Ci";
    explanation = `${UNIT_FACTS.ciInBq}. Divide by ${formatConverter(CI_IN_BQ)} to get Ci (bq_to_ci); multiply Ci by ${formatConverter(CI_IN_BQ)} to get Bq (ci_to_bq). Round-trip: ci_to_bq(bq_to_ci(${formatConverter(activityBq)})) = ${formatConverter(ciToBq(ci))} Bq.`;
    code = `from pydecay import bq_to_ci, ci_to_bq

bq = ${activityLiteral(activityBq)}
print(bq_to_ci(bq))  # ${formatConverter(ci)} Ci
print(ci_to_bq(${ci === 0 ? "0.0" : formatConverter(ci).replace(/,/g, "")}))  # ${formatConverter(activityBq)} Bq`;
  } else if (mode === "mass") {
    const fromAtomsG = atomsToGrams(atomsN, massU);
    const fromMassAtoms = gramsToAtoms(massG, massU);
    primaryLabel = "ATOMS";
    primaryValue = formatConverter(atomsN);
    primaryUnit = "atoms";
    secondaryLabel = "MASS (from atoms)";
    secondaryValue = formatConverter(fromAtomsG);
    secondaryUnit = "g";
    explanation = `Atomic mass ${massU} u · N_A = ${formatConverter(AVOGADRO_PER_MOL)}. ${formatConverter(atomsN)} atoms → ${formatConverter(fromAtomsG)} g; ${massG} g → ${formatConverter(fromMassAtoms)} atoms.`;
    code = `from pydecay import atoms_to_grams, grams_to_atoms

N_A = ${AVOGADRO_PER_MOL}
u = ${massU}
print(atoms_to_grams(${atomsInput}, u))  # ${formatConverter(fromAtomsG)} g
print(grams_to_atoms(${massG}, u))       # ${formatConverter(fromMassAtoms)} atoms`;
  } else if (mode === "time") {
    try {
      const seconds = toSeconds(timeInput.trim() === "" ? "8.02 days" : timeInput);
      primaryLabel = "INPUT TIME";
      primaryValue = timeInput.trim() || "8.02 days";
      primaryUnit = "";
      secondaryLabel = "SECONDS";
      secondaryValue = formatConverter(seconds);
      secondaryUnit = "s";
      explanation = `Canonical unit is the second. "8.02 days" × 86400 = 692,992 s (I-131 half-life ≈ 692,988.48 s in ICRP-107).`;
      code = `from pydecay import to_seconds

print(to_seconds(${JSON.stringify(timeInput.trim() || "8.02 days")}))  # ${formatConverter(seconds)} s`;
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
      primaryLabel = "INPUT TIME";
      primaryValue = timeInput;
      primaryUnit = "";
      secondaryLabel = "SECONDS";
      secondaryValue = "—";
      secondaryUnit = "s";
      explanation =
        'Enter a non-negative number or a unit string such as "8.02 days" or "6 hours".';
      code = `from pydecay import to_seconds\n\nto_seconds(${JSON.stringify(timeInput)})`;
    }
  } else {
    const halfLifeS = halfLifeDays * 86400;
    const lam = decayConstant(halfLifeS);
    const tau = meanLifetimeS(lam);
    primaryLabel = "HALF-LIFE";
    primaryValue = formatConverter(halfLifeS);
    primaryUnit = "s";
    secondaryLabel = "λ / τ";
    secondaryValue = `${formatConverter(lam)} / ${formatConverter(tau)}`;
    secondaryUnit = "1/s · s";
    explanation = `${halfLifeDays} days = ${formatConverter(halfLifeS)} s. λ = ln(2)/T½ = ${formatConverter(lam)} s⁻¹; τ = 1/λ = ${formatConverter(tau)} s ≈ ${formatConverter(tau / 86400)} days.`;
    code = `from pydecay import decay_constant, mean_lifetime_s, to_seconds

t_half = to_seconds("${halfLifeDays} days")  # ${formatConverter(halfLifeS)} s
lam = decay_constant(t_half)   # ${formatConverter(lam)} 1/s
tau = mean_lifetime_s(lam)     # ${formatConverter(tau)} s`;
  }

  const activeMode = converterModes.find((item) => item.id === mode) ?? converterModes[0];

  return (
    <section className="unit-converter-section section-shell" id="unit-converter">
      <SectionHeading
        number="02"
        label="UNIT CONVERTER"
        title="Units, in real time."
        description="The same seven helpers now exported from the package root — type a value and watch Bq↔Ci, atoms↔grams, time→seconds, and T½→λ/τ compute live, with the exact Python you would run."
      />
      <Reveal className="workbench converter-workbench">
        <div className="workbench-controls">
          <div className="workbench-caption">
            <span className="caption-square" /> CONVERSION MODE <span>02 / 04</span>
          </div>

          <div className="converter-mode-tabs" role="tablist" aria-label="Unit conversion mode">
            {converterModes.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={mode === item.id}
                className={mode === item.id ? "is-active" : ""}
                onClick={() => setMode(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <p className="field-hint">Formula: {activeMode.formula}</p>

          {mode === "activity" && (
            <>
              <label className="field-label" htmlFor="converter-activity">
                ACTIVITY
              </label>
              <div className="number-wrap">
                <input
                  id="converter-activity"
                  type="text"
                  inputMode="decimal"
                  value={activityInput}
                  onChange={(event) => setActivityInput(event.target.value)}
                />
                <span>Bq</span>
              </div>
              <p className="field-hint">Try 3.7e10 (= 1 Ci) or 1e6 (1 MBq)</p>
            </>
          )}

          {mode === "mass" && (
            <>
              <label className="field-label" htmlFor="converter-atoms">
                ATOM COUNT
              </label>
              <div className="number-wrap">
                <input
                  id="converter-atoms"
                  type="text"
                  inputMode="decimal"
                  value={atomsInput}
                  onChange={(event) => setAtomsInput(event.target.value)}
                />
                <span>atoms</span>
              </div>
              <label className="field-label" htmlFor="converter-mass-g">
                MASS
              </label>
              <div className="number-wrap">
                <input
                  id="converter-mass-g"
                  type="text"
                  inputMode="decimal"
                  value={massGInput}
                  onChange={(event) => setMassGInput(event.target.value)}
                />
                <span>g</span>
              </div>
              <label className="field-label" htmlFor="converter-mass-u">
                ATOMIC MASS (u)
              </label>
              <div className="number-wrap">
                <input
                  id="converter-mass-u"
                  type="text"
                  inputMode="decimal"
                  value={massUInput}
                  onChange={(event) => setMassUInput(event.target.value)}
                />
                <span>u</span>
              </div>
              <p className="field-hint">I-131 ≈ 130.9061 u · N_A = 6.02214076e23</p>
            </>
          )}

          {mode === "time" && (
            <>
              <label className="field-label" htmlFor="converter-time">
                TIME
              </label>
              <div className="number-wrap">
                <input
                  id="converter-time"
                  type="text"
                  value={timeInput}
                  onChange={(event) => setTimeInput(event.target.value)}
                />
                <span>str</span>
              </div>
              <p className="field-hint">Examples: 8.02 days · 6 hours · 90 · 1.5e5 seconds</p>
            </>
          )}

          {mode === "decay" && (
            <>
              <label className="field-label" htmlFor="converter-half-life">
                HALF-LIFE
              </label>
              <div className="number-wrap">
                <input
                  id="converter-half-life"
                  type="text"
                  inputMode="decimal"
                  value={halfLifeDaysInput}
                  onChange={(event) => setHalfLifeDaysInput(event.target.value)}
                />
                <span>days</span>
              </div>
              <p className="field-hint">I-131 ≈ 8.0228 days · Co-60 ≈ 1925.23 days</p>
            </>
          )}

          <div className="result-readout" aria-live="polite">
            <span>{primaryLabel}</span>
            <div className="converter-primary">
              {primaryValue} {primaryUnit && <small>{primaryUnit}</small>}
            </div>
            <p>
              {secondaryLabel && (
                <>
                  {secondaryLabel}: <strong>{secondaryValue}</strong>
                  {secondaryUnit ? ` ${secondaryUnit}` : ""}
                </>
              )}
            </p>
            {error && <p className="converter-error">{error}</p>}
          </div>
        </div>

        <div className="workbench-output converter-output">
          <div className="output-topline">
            <span>
              LIVE CONVERSION <i /> {activeMode.label}
            </span>
            <span>{activeMode.formula}</span>
          </div>
          <div className="converter-explain">
            <span className="converter-explain-label">HOW IT WORKS</span>
            <p>{explanation}</p>
            <div className="converter-facts">
              <div>
                <span>EXACT</span>
                <strong>{UNIT_FACTS.ciInBq}</strong>
              </div>
              <div>
                <span>EXACT</span>
                <strong>{UNIT_FACTS.avogadro}</strong>
              </div>
              <div>
                <span>DECAY</span>
                <strong>{UNIT_FACTS.ln2}</strong>
              </div>
            </div>
            <div className="converter-equations">
              <div>
                <span>→ Ci</span>
                <code>bq_to_ci(Bq) = Bq / 3.7e10</code>
                <em>
                  {formatConverter(activityBq)} / {formatConverter(CI_IN_BQ)} ={" "}
                  {formatConverter(bqToCi(activityBq))} Ci
                </em>
              </div>
              <div>
                <span>→ g</span>
                <code>atoms_to_grams(N, u) = N * u / N_A</code>
                <em>
                  {formatConverter(atomsN)} × {massU} / {formatConverter(AVOGADRO_PER_MOL)} ={" "}
                  {formatConverter(atomsToGrams(atomsN, massU))} g
                </em>
              </div>
              <div>
                <span>→ s</span>
                <code>to_seconds("8.02 days") = 8.02 * 86400</code>
                <em>8.02 × 86400 = {formatConverter(8.02 * 86400)} s</em>
              </div>
            </div>
          </div>
          <CodeBlock code={code} label="GENERATED PYTHON" compact className="workbench-code" />
        </div>
      </Reveal>
      <p className="workbench-footnote">
        Preview calculated in your browser — same formulas as pydecay 0.6.0 top-level exports (
        <code>to_seconds</code>, <code>bq_to_ci</code>, <code>ci_to_bq</code>,{" "}
        <code>atoms_to_grams</code>, <code>grams_to_atoms</code>, <code>decay_constant</code>,{" "}
        <code>mean_lifetime_s</code>).
      </p>
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
  graphic: "single" | "chain" | "stability" | "branching" | "dose" | "shielding";
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
    detail:
      "Bateman's closed form handles well-separated linear chains, all the way to a stable daughter.",
    code: `from pydecay import DecayChain\n\nchain = DecayChain([0.693, 0.0], names=["parent", "stable"])\nprint(chain.at(t="1 days", n0={"parent": 1e6, "stable": 0.0}))`,
    graphic: "chain",
  },
  {
    number: "03",
    title: "Numerical stability",
    summary: "Reliable even when rates converge.",
    tag: "MATRIX EXPONENTIAL",
    detail:
      "Near-degenerate decay constants, branching, and nonzero daughter populations dispatch to scipy.linalg.expm.",
    code: `from pydecay import DecayChain\n\nchain = DecayChain([0.6931, 0.6932, 0.0], names=["P", "D", "S"])\nchain.at(t=1.0, n0={"P": 1e6, "D": 0.0, "S": 0.0})`,
    graphic: "stability",
  },
  {
    number: "04",
    title: "Branching paths",
    summary: "One parent. Multiple outcomes.",
    tag: "BRANCHING TOPOLOGIES",
    detail:
      "Model star-shaped branches with fractions up to one; any remainder flows to an untracked sink.",
    code: `from pydecay import DecayChain\n\nb = DecayChain.branching(\n    parent="P", branches={"D1": 0.6, "D2": 0.3},\n    lambdas={"P": 0.7, "D1": 1e-5, "D2": 2e-5},\n)`,
    graphic: "branching",
  },
  {
    number: "05",
    title: "Dose rates",
    summary: "Point source to dose, in one call.",
    tag: "EXPOSURE & AIR KERMA",
    detail:
      "Curated exposure-rate constants for 34 photon-emitting nuclides give air-kerma or ambient dose-equivalent rates at any distance.",
    code: `from pydecay import dose_rate\n\nrate = dose_rate(1e6, "Co-60", r=1.0)  # Gy/h\nambient = dose_rate(1e6, "Co-60", r=1.0, quantity="ambient")  # Sv/h\nprint(rate, ambient)`,
    graphic: "dose",
  },
  {
    number: "06",
    title: "Shielding",
    summary: "Beer-Lambert, no guesswork.",
    tag: "NARROW-BEAM ATTENUATION",
    detail:
      "NIST XCOM coefficients for seven materials: half-value layers, tenth-value layers, and transmission through any slab.",
    code: `from pydecay import hvl_slab, transmit_slab\n\nprint(hvl_slab("lead", 1.25))  # m\nprint(transmit_slab(1.0, "lead", 0.01, 1.25))  # 51% through 1 cm`,
    graphic: "shielding",
  },
];

function FeatureGraphic({ type }: { type: Feature["graphic"] }) {
  if (type === "single") {
    return (
      <div className="formula-graphic" aria-label="Exponential single-isotope decay formula">
        <span className="formula-small">THE FUNDAMENTAL EQUATION</span>
        <div>
          N(t) <em>=</em> N<sub>0</sub> e<sup>-&lambda;t</sup>
        </div>
        <span className="formula-bottom">
          &lambda; = ln(2) / t<sub>1/2</sub> &nbsp;&nbsp; A(t) = &lambda;N(t)
        </span>
      </div>
    );
  }

  if (type === "stability") {
    return (
      <div
        className="formula-graphic stability-graphic"
        aria-label="Matrix exponential solver formula"
      >
        <span className="formula-small">WHEN CLOSED FORM NEEDS A GUARD</span>
        <div>
          n(t) <em>=</em> e<sup>Mt</sup> n<sub>0</sub>
        </div>
        <span className="formula-bottom">NEAR-EQUAL RATES / FINITE RESULTS / NO CANCELLATION</span>
      </div>
    );
  }

  if (type === "chain") {
    return (
      <svg
        className="topology-graphic"
        viewBox="0 0 640 200"
        role="img"
        aria-label="Parent nuclide decays into daughter and then stable nuclide"
      >
        <path d="M150 93H258M373 93H482" className="topology-line" />
        <path d="m250 85 10 8-10 8m224-16 10 8-10 8" className="topology-arrow" />
        <rect x="34" y="48" width="116" height="90" className="topology-node active" />
        <rect x="258" y="48" width="116" height="90" className="topology-node" />
        <rect x="482" y="48" width="116" height="90" className="topology-node" />
        <text x="92" y="100" textAnchor="middle" className="topology-symbol active-text">
          P
        </text>
        <text x="316" y="100" textAnchor="middle" className="topology-symbol">
          D
        </text>
        <text x="540" y="100" textAnchor="middle" className="topology-symbol">
          S
        </text>
        <text x="92" y="161" textAnchor="middle" className="topology-caption">
          PARENT
        </text>
        <text x="316" y="161" textAnchor="middle" className="topology-caption">
          DAUGHTER
        </text>
        <text x="540" y="161" textAnchor="middle" className="topology-caption">
          STABLE
        </text>
      </svg>
    );
  }

  if (type === "dose") {
    return (
      <div className="formula-graphic" aria-label="Point-source inverse-square dose rate formula">
        <span className="formula-small">POINT SOURCE AT DISTANCE r</span>
        <div>
          Ξ(r) <em>=</em> Γ · A / r²
        </div>
        <span className="formula-bottom">
          Γ [R·cm²/mCi/h] &nbsp;&nbsp; 1 R = 8.76 mGy IN AIR &nbsp;&nbsp; AMBIENT VIA H*(10) AT 1.25
          MeV
        </span>
      </div>
    );
  }

  if (type === "shielding") {
    return (
      <div className="formula-graphic" aria-label="Beer-Lambert narrow-beam attenuation formula">
        <span className="formula-small">NARROW-BEAM ATTENUATION</span>
        <div>
          I <em>=</em> I<sub>0</sub> e<sup>-&mu;x</sup>
        </div>
        <span className="formula-bottom">
          HVL = ln2 / &mu; &nbsp;&nbsp; TVL = ln10 / &mu; &nbsp;&nbsp; NIST XCOM / 7 MATERIALS
        </span>
      </div>
    );
  }

  return (
    <svg
      className="topology-graphic branching-graphic"
      viewBox="0 0 640 200"
      role="img"
      aria-label="A parent branches to two daughters at 60 and 30 percent"
    >
      <path d="M150 97H260L377 45H480M260 97l117 65h103" className="topology-line" />
      <path d="M472 37l10 8-10 8M472 154l10 8-10 8" className="topology-arrow" />
      <rect x="34" y="52" width="116" height="90" className="topology-node active" />
      <rect x="480" y="12" width="116" height="68" className="topology-node" />
      <rect x="480" y="128" width="116" height="68" className="topology-node" />
      <text x="92" y="104" textAnchor="middle" className="topology-symbol active-text">
        P
      </text>
      <text x="538" y="58" textAnchor="middle" className="topology-symbol">
        D1
      </text>
      <text x="538" y="175" textAnchor="middle" className="topology-symbol">
        D2
      </text>
      <text x="332" y="42" textAnchor="middle" className="topology-caption">
        60%
      </text>
      <text x="334" y="151" textAnchor="middle" className="topology-caption">
        30%
      </text>
      <text x="92" y="169" textAnchor="middle" className="topology-caption">
        10% UNTRACKED
      </text>
    </svg>
  );
}

function Capabilities() {
  const [active, setActive] = useState(1);
  const feature = features[active];

  return (
    <section className="capabilities-section section-shell" id="capabilities">
      <SectionHeading
        number="03"
        label="THE ENGINE"
        title="More than a decay curve."
        description="ICRP-107-sourced nuclides and unit-aware inputs meet an analytical solver that knows when to take the numerically stable route."
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
              <span className="feature-text">
                <strong>{item.title}</strong>
                <small>{item.summary}</small>
              </span>
              <ArrowUpRight size={21} strokeWidth={1.5} />
            </button>
          ))}
        </div>

        <div
          className="feature-panel"
          id="feature-panel"
          role="tabpanel"
          aria-labelledby={`feature-tab-${active}`}
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={feature.number}
              className="feature-panel-inner"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.24 }}
            >
              <div className="feature-panel-top">
                <span>{feature.tag}</span>
                <span>
                  0{active + 1} / 0{features.length}
                </span>
              </div>
              <FeatureGraphic type={feature.graphic} />
              <p className="feature-detail">{feature.detail}</p>
              <CodeBlock
                code={feature.code}
                label="EXAMPLE / PYTHON"
                compact
                className="feature-code"
              />
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
  return (
    <div className="property-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ElementPanel({
  element,
  onTryNuclide,
}: {
  element: ElementInfo;
  onTryNuclide: (id: string) => void;
}) {
  const featuredId = featuredIsotopes[element.symbol];
  const nuclide = demoNuclides.find((item) => item.id === featuredId);
  const wikiUrl = `https://en.wikipedia.org/wiki/${encodeURIComponent(element.name.replace(/ /g, "_"))}`;

  return (
    <aside
      className="element-panel"
      id="element-details"
      aria-label="Selected element information"
      aria-live="polite"
    >
      <div className="element-panel-header">
        <span>ELEMENT FILE / {String(element.number).padStart(3, "0")}</span>
        <span className="panel-crosshair" aria-hidden="true">
          +
        </span>
      </div>
      <motion.div
        key={element.number}
        className="element-panel-body"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.16 }}
      >
        <div
          className="element-identity"
          style={
            { "--identity-color": categoryColors[element.category] ?? "#a0a39c" } as CSSProperties
          }
        >
          <strong>{element.symbol}</strong>
          <span>{element.number}</span>
        </div>
        <div className="element-name-block">
          <h3>{element.name}</h3>
          <span>{element.category.toUpperCase()}</span>
        </div>
        <p className="element-description">
          Atomic number {element.number} identifies the number of protons in its nucleus.{" "}
          {element.name} sits in period {element.period} of the periodic table.
        </p>
        <div className="property-list">
          <PropertyRow label="ATOMIC MASS" value={`${element.mass} u`} />
          <PropertyRow
            label="PERIOD / GROUP"
            value={`${element.period} / ${element.group ?? "f-block"}`}
          />
          <PropertyRow label="ELECTRON CONFIG." value={element.configuration} />
          <PropertyRow
            label="STATE AT ROOM TEMP."
            value={element.state.charAt(0).toUpperCase() + element.state.slice(1)}
          />
          <PropertyRow
            label="ELECTRONEGATIVITY"
            value={
              element.electronegativity === null
                ? "Not available"
                : String(element.electronegativity)
            }
          />
          <PropertyRow
            label="MELTING POINT"
            value={element.meltingPoint === null ? "Not available" : `${element.meltingPoint} K`}
          />
        </div>
        {nuclide && (
          <div className="element-nuclide">
            <span>EXPLORE IN PYDECAY</span>
            <div>
              <strong>{nuclide.id}</strong>
              <small>t1/2 = {nuclide.displayHalfLife}</small>
            </div>
            <button type="button" onClick={() => onTryNuclide(nuclide.id)}>
              SIMULATE THIS NUCLIDE <ArrowUpRight size={16} />
            </button>
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
        .filter(
          (element) =>
            element.name.toLowerCase().includes(term) ||
            element.symbol.toLowerCase().includes(term) ||
            String(element.number) === term,
        )
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
      const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth";
      window.setTimeout(
        () =>
          document.getElementById("element-details")?.scrollIntoView({ behavior, block: "start" }),
        30,
      );
    }
  }

  return (
    <section className="periodic-section section-shell" id="elements">
      <SectionHeading
        number="04"
        label="THE ELEMENTS"
        title="A field guide to matter."
        description="All 118 elements, one place to explore. Hover, focus, or tap an element to open its information file."
      />
      <div className="periodic-toolbar">
        <span>
          <span className="caption-square" /> PERIODIC TABLE / 118 ELEMENTS
        </span>
        <div className="element-search">
          <Search size={17} aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search an element"
            aria-label="Search elements by name, symbol, or atomic number"
          />
          {query && (
            <button type="button" onClick={() => setQuery("")} aria-label="Clear search">
              <X size={16} />
            </button>
          )}
        </div>
      </div>
      {matchingNumbers && matchingNumbers.size === 0 && (
        <p className="search-no-results">
          No element matches "{query}". Try a name, symbol, or atomic number.
        </p>
      )}
      <div className="periodic-layout">
        <div className="periodic-table-side">
          <div
            className="periodic-scroll"
            tabIndex={0}
            aria-label="Periodic table, scroll horizontally on smaller screens"
          >
            <div className="table-canvas">
              <div className="group-numbers" aria-hidden="true">
                {Array.from({ length: 18 }, (_, index) => (
                  <span key={index}>{String(index + 1).padStart(2, "0")}</span>
                ))}
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
                      style={
                        {
                          gridColumn: element.column,
                          gridRow: element.row,
                          "--tile-accent": categoryColors[element.category] ?? "#a0a39c",
                        } as CSSProperties
                      }
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
                <div
                  className="series-placeholder"
                  style={{ gridColumn: 3, gridRow: 6 }}
                  aria-hidden="true"
                >
                  57-71<small>La-Lu</small>
                </div>
                <div
                  className="series-placeholder"
                  style={{ gridColumn: 3, gridRow: 7 }}
                  aria-hidden="true"
                >
                  89-103<small>Ac-Lr</small>
                </div>
                <span className="series-label" style={{ gridColumn: "1 / 3", gridRow: 9 }}>
                  LANTHANIDES
                </span>
                <span className="series-label" style={{ gridColumn: "1 / 3", gridRow: 10 }}>
                  ACTINIDES
                </span>
              </div>
            </div>
          </div>
          <div className="table-note">
            <span>
              <i /> FEATURED IN THE PLAYGROUND
            </span>
            <span>
              {liveData ? "PROPERTIES: LIVE REFERENCE DATA" : "PROPERTIES: BUNDLED REFERENCE DATA"}
            </span>
          </div>
        </div>
        <ElementPanel element={selected} onTryNuclide={onTryNuclide} />
      </div>
      <p className="periodic-disclaimer">
        The table is an element reference. pydecay bundles 1252 ICRP-107 radionuclides (1498 records
        including stable endpoints), not every isotope of every element.
      </p>
    </section>
  );
}

function Verification() {
  const [openId, setOpenId] = useState<string | null>(null);
  const checks = [
    {
      number: "01",
      title: "Known values, independently asserted.",
      detail: "1000 Bq of I-131 becomes 500 Bq after one half-life and 31.25 Bq after five.",
      file: "tests/test_known_values.py",
      note: "Expected values are re-derived from the bundled half-lives themselves — the reference table is not the assertion source.",
      snippet: `def test_i131_reference_example_explicit():
    i131 = Nuclide.load("I-131")
    a1 = decayed_activity(A0=1000.0, half_life=i131.half_life, time=i131.half_life)
    a5 = decayed_activity(A0=1000.0, half_life=i131.half_life, time=5 * i131.half_life)
    assert a1 == pytest.approx(500.0, rel=1e-12)
    assert a5 == pytest.approx(31.25, rel=1e-12)`,
    },
    {
      number: "02",
      title: "Solvers checked against each other.",
      detail:
        "Bateman and matrix-exponential results agree to 1e-10; near-equal rates stay finite.",
      file: "tests/test_solver.py",
      note: "Closed-form Bateman and scipy.linalg.expm paths are asserted equal; near-degenerate λ falls back without NaNs.",
      snippet: `def test_bateman_agrees_with_expm_well_separated():
    g = DecayGraph.linear([1.0, 0.01, 0.0002])
    for t in (0.5, 10.0, 100.0):
        np.testing.assert_allclose(solve(g, [1e9, 0.0, 0.0], t),
                                   _expm_reference(g, [1e9, 0.0, 0.0], t),
                                   rtol=1e-10, atol=1e-20)

def test_spec_2_3_near_degenerate_is_finite():
    out = solve(DecayGraph.linear([0.6931, 0.6932]), [1.0, 0.0], 1.0)
    assert np.all(np.isfinite(out))`,
    },
    {
      number: "03",
      title: "Another library, another answer.",
      detail:
        "Differential tests against radioactivedecay (ICRP-107) fail beyond 1e-3 relative drift.",
      file: "tests/test_crosscheck.py",
      note: "Every overlapping nuclide is compared half-life to half-life; IAEA vs ICRP-107 source gaps are listed as accepted deviations.",
      snippet: `REL_TOL = 1e-3

def test_half_life_drift_within_tolerance(capsys):
    for name in names:
        rel = abs(ours[name].half_life_s - rr_half_life(name)) / rr_half_life(name)
        if rel > REL_TOL and name not in ACCEPTED_DEVIATIONS:
            failures.append((name, rel))
    assert not failures, f"half-life drift beyond {REL_TOL}: {failures}"`,
    },
  ];

  return (
    <section className="verification-section section-shell" id="verification">
      <SectionHeading
        number="05"
        label="VERIFICATION"
        title="Numbers you can defend."
        description="Scientific software earns trust through reproducible comparisons, not just clean-looking curves."
      />
      <Reveal className="verification-list">
        {checks.map((check) => {
          const open = openId === check.number;
          const panelId = `verification-panel-${check.number}`;
          return (
            <div
              className={open ? "verification-row is-open" : "verification-row"}
              key={check.number}
            >
              <span className="verification-meta">{check.number} / TEST</span>
              <h3>{check.title}</h3>
              <p>{check.detail}</p>
              <button
                type="button"
                className="verification-plus"
                aria-expanded={open}
                aria-controls={panelId}
                aria-label={open ? `Collapse test ${check.number}` : `Expand test ${check.number}`}
                onClick={() => setOpenId(open ? null : check.number)}
              >
                <span aria-hidden="true">{open ? "×" : "+"}</span>
              </button>
              <div className="verification-detail" id={panelId} hidden={!open}>
                <span className="verification-file">{check.file}</span>
                <p>{check.note}</p>
                <pre className="verification-snippet">
                  <code>{check.snippet}</code>
                </pre>
                <a
                  className="verification-source"
                  href={`${GITHUB_URL}/blob/main/${check.file}`}
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  VIEW SOURCE <ArrowUpRight size={14} />
                </a>
              </div>
            </div>
          );
        })}
      </Reveal>
    </section>
  );
}

function ClosingCallout() {
  const nav = useInternalNav();

  return (
    <section className="closing-section section-shell">
      <Reveal className="closing-inner">
        <span className="section-kicker">
          <span>06 /</span> START BUILDING
        </span>
        <h2>
          Time to make
          <br />
          <span>something precise.</span>
        </h2>
        <div className="closing-bottom">
          <p>Install the package, read the guide, and put reliable decay mathematics to work.</p>
          <a href="/docs" className="button-primary" onClick={nav("/docs")}>
            OPEN DOCUMENTATION <ArrowUpRight size={18} />
          </a>
        </div>
      </Reveal>
    </section>
  );
}

function HomePage() {
  const [selectedId, setSelectedId] = useState("I-131");

  function tryNuclide(id: string) {
    setSelectedId(id);
    navigate("/playground");
    scrollToId("playground");
  }

  return (
    <main>
      <Hero />
      <Playground selectedId={selectedId} onSelect={setSelectedId} />
      <UnitConverter />
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
  { id: "user-guide", label: "User guide" },
  { id: "quickstart", label: "Quickstart" },
  { id: "single-isotope", label: "Single isotope" },
  { id: "decay-chains", label: "Decay chains" },
  { id: "branching", label: "Branching" },
  { id: "spectra", label: "Spectra" },
  { id: "solver", label: "Solver strategy" },
  { id: "data-units", label: "Data & units" },
  { id: "verification", label: "Verification" },
  { id: "changelog", label: "Changelog" },
];

function DocsSection({
  id,
  number,
  title,
  children,
}: {
  id: string;
  number: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="docs-section" id={id}>
      <span className="docs-section-number">{number} / GUIDE</span>
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function DocsPage({ path }: { path: string }) {
  const activeSection = path.startsWith("/docs/")
    ? path.slice("/docs/".length) || "installation"
    : "installation";

  function goSection(event: MouseEvent<HTMLAnchorElement>, id: string) {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(`/docs/${id}`);
    scrollToId(id);
  }

  return (
    <main className="docs-page">
      <div className="docs-masthead section-shell">
        <span className="section-kicker">
          <span>PYDECAY /</span> FIELD MANUAL
        </span>
        <h1>
          Documentation<span>.</span>
        </h1>
        <p>
          Everything you need to model radioactive decay with confidence, from your first half-life
          to a branching chain.
        </p>
        <div className="docs-masthead-meta">
          <span>PYTHON 3.10+</span>
          <span>MIT + ICRP-107 DATA</span>
          <span>VERSION 0.6.0</span>
        </div>
      </div>

      <div className="docs-layout section-shell">
        <aside className="docs-sidebar" aria-label="Documentation sections">
          <span className="docs-sidebar-label">CONTENTS / 11</span>
          <nav>
            {docsNavigation.map((item, index) => (
              <a
                key={item.id}
                href={`/docs/${item.id}`}
                className={activeSection === item.id ? "current" : ""}
                onClick={(event) => goSection(event, item.id)}
              >
                <span>{String(index + 1).padStart(2, "0")}</span>
                {item.label}
              </a>
            ))}
          </nav>
          <a
            className="docs-sidebar-source"
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer noopener"
          >
            VIEW SOURCE <ArrowUpRight size={15} />
          </a>
        </aside>

        <article className="docs-article">
          <DocsSection id="installation" number="01" title="Installation">
            <p>
              Install pydecay from PyPI in a Python 3.10 or newer environment. NumPy, SciPy, and
              Pint are installed as runtime dependencies.
            </p>
            <CodeBlock code="pip install pydecay" label="TERMINAL" />
            <div className="docs-inline-note">
              <span>REQUIRES</span>
              <strong>Python &gt;= 3.10</strong>
              <span>DEPENDS ON</span>
              <strong>numpy / scipy / pint</strong>
            </div>
          </DocsSection>

          <DocsSection id="user-guide" number="02" title="User guide — every function, simply">
            <p>
              This is the zero-to-working tour. Every public function, what it is for, and a
              runnable snippet. Copy any block into a file and run it.
            </p>

            <h3 className="docs-subhead">How much is left? (3 functions)</h3>
            <p>
              <strong>
                1. <code>decayed_activity(A0, half_life, time)</code>
              </strong>{" "}
              — starting activity → activity now.
            </p>
            <CodeBlock
              code={`from pydecay import decayed_activity\n# 1000 Bq of I-131 after one half-life -> 500 Bq\nprint(decayed_activity(A0=1000.0, half_life="8.02 days", time="8.02 days"))  # 500.0`}
            />
            <p>
              <strong>
                2. <code>decayed_atoms(N0, half_life, time)</code>
              </strong>{" "}
              — starting atom count → atoms left.
            </p>
            <CodeBlock
              code={`from pydecay import decayed_atoms\nprint(decayed_atoms(N0=1_000_000, half_life="8.02 days", time="24 hours"))`}
            />
            <p>
              <strong>
                3. <code>remaining_fraction(half_life, time)</code>
              </strong>{" "}
              — pure percent left (0–1), no starting amount needed.
            </p>
            <CodeBlock
              code={`from pydecay import remaining_fraction\n# After 5 half-lives only 3.125% remains\nprint(remaining_fraction(half_life="8.02 days", time="8.02 days"))  # 0.5\nprint(remaining_fraction(half_life="8.02 days", time=5 * 8.02 * 86400))  # 0.03125`}
            />
            <div className="docs-rule">
              <span>MENTAL MATH</span>
              <p>
                1 half-life → 50% left. 2 → 25%. 3 → 12.5%. 5 → 3.125%. Multiply any starting number
                by <code>remaining_fraction</code>.
              </p>
            </div>

            <h3 className="docs-subhead">
              Instantaneous rates &amp; ODE residual <span>(0.5.0)</span>
            </h3>
            <p>
              <strong>Use case:</strong> “How fast is it changing right now?” — <code>dn_dt</code> /{" "}
              <code>da_dt</code> return dN/dt and dA/dt;
              <code>decay_ode_residual</code> checks a numerical derivative against the law.
            </p>
            <CodeBlock
              code={`from pydecay import dn_dt, da_dt, decay_ode_residual, Inventory\n\n# dN/dt = -lambda*N  (atoms/s; negative = losing atoms)\nprint(dn_dt(1e6, "8.02 days"))            # atoms/s\n\n# dA/dt = -lambda*A(t)  (Bq/s at t=0)\nprint(da_dt(1000.0, "8.02 days", 0.0))    # Bq/s\n\n# Residual dN/dt + lambda*N — exactly 0 on an analytic trajectory\nprint(decay_ode_residual(1e6, 8.02 * 86400))  # 0.0\n\n# Check a numerical derivative against the law\nprint(decay_ode_residual(1e6, 8.02 * 86400, dn_dt_value=-1e6 / (8.02 * 86400)))  # ~0\n\n# Multi-nuclide: joint generator rates for the full closure\ninv = Inventory({"Mo-99": 1e6}, units="Bq")\nprint(inv.instantaneous_rates())  # dict species -> atoms/s`}
            />
            <div className="docs-inline-note">
              <span>ATOMS</span>
              <strong>dn_dt(N, half_life)</strong>
              <span>ACTIVITY</span>
              <strong>da_dt(A0, half_life, time)</strong>
              <span>ODE</span>
              <strong>decay_ode_residual(...)</strong>
              <span>CLOSURE</span>
              <strong>Inventory.instantaneous_rates()</strong>
            </div>

            <h3 className="docs-subhead">
              Look up a real nuclide: <code>Nuclide</code>
            </h3>
            <p>
              <strong>Use case:</strong> “What is the half-life of I-131, and where did the number
              come from?” 1252 ICRP-107 radionuclides (+ 246 stable endpoints = 1498 records) ship
              with the package.
            </p>
            <CodeBlock
              code={`from pydecay import Nuclide\n\ni131 = Nuclide.load("I-131")\nprint(i131.half_life)      # pint Quantity (seconds)\nprint(i131.half_life_s)    # plain seconds: 692988.48\nprint(i131.lambda_)        # decay constant 1/s\nprint(i131.atomic_mass_u)  # mass in u\nprint(i131.source)         # "ICRP-107"\n\nall_nuclides = Nuclide.load_all()  # 1252 radionuclides + 246 stable = 1498 records`}
            />
            <div className="docs-inline-note">
              <span>LOOKUP</span>
              <strong>Nuclide.load / Nuclide.load_all</strong>
              <span>ACTIVITY FROM ATOMS</span>
              <strong>.activity(N, t=...)</strong>
            </div>

            <h3 className="docs-subhead">
              Follow a decay chain: <code>DecayChain</code>
            </h3>
            <p>
              <strong>Use case:</strong> parent → daughter → stable. How much of each at time t?
            </p>
            <CodeBlock
              code={`from pydecay import DecayChain\n\n# From real nuclide names (half-lives auto-loaded)\nchain = DecayChain.from_isotopes(["Sr-90", "Y-90"])\nprint(chain.at(t="1 day", n0={"Sr-90": 1e6, "Y-90": 0.0}))      # atom counts\nprint(chain.activity(t="1 day", n0={"Sr-90": 1e6, "Y-90": 0.0})) # Bq of each\n\n# Or from raw decay constants (1/s), parent first; 0 = stable\nchain2 = DecayChain([0.693, 0.0], names=["parent", "stable"])\nprint(chain2.at(t="1 days", n0={"parent": 1e6, "stable": 0.0}))`}
            />
            <p>
              Methods: <code>.at(t, n0)</code> → atoms · <code>.activity(t, n0)</code> → Bq ·{" "}
              <code>.names</code> · <code>.lambdas</code>. Omit <code>n0</code> and the parent
              starts at 1.0.
            </p>

            <h3 className="docs-subhead">One parent, multiple outcomes: branching</h3>
            <CodeBlock
              code={`from pydecay import DecayChain\n\nb = DecayChain.branching(\n    parent="P",\n    branches={"D1": 0.6, "D2": 0.3},   # fractions; sum <= 1\n    lambdas={"P": 0.7, "D1": 1e-5, "D2": 2e-5},\n)\nprint(b.at(t="1 day"))       # atoms of P, D1, D2\nprint(b.activity(t="1 day")) # Bq of each`}
            />
            <div className="docs-rule">
              <span>BRANCH RULE</span>
              <p>
                Fractions must sum to at most 1.0. If they sum to 0.9, the remaining 10% leaves as
                an untracked sink.
              </p>
            </div>

            <h3 className="docs-subhead">
              Radiation spectra: <code>emissions</code> &amp; <code>beta_spectrum</code>
            </h3>
            <p>
              <strong>Use case:</strong> “What radiation lines does this nuclide emit?” / “Plot the
              beta energy spectrum.”
            </p>
            <CodeBlock
              code={`from pydecay import emissions, beta_spectrum\n\nrows = emissions("Ac-223")            # list of dicts: E_MeV, prob, code...\nE, A = beta_spectrum("Sr-90")         # two parallel lists in MeV\nprint(len(rows), len(E))              # e.g. 480, 102`}
            />
            <p>
              Lazy-loaded on first call (does not slow <code>import pydecay</code>). Stable nuclides
              raise <code>DataFormatError</code>; unknown names raise{" "}
              <code>NuclideNotFoundError</code>.
            </p>

            <h3 className="docs-subhead">Errors — what you catch</h3>
            <div className="docs-check-list">
              <div>
                <span>01</span>
                <strong>NuclideNotFoundError</strong>
                <code>Nuclide.load("Xx-999")</code>
              </div>
              <div>
                <span>02</span>
                <strong>InvalidTimeError</strong>
                <code>time &lt; 0</code>
              </div>
              <div>
                <span>03</span>
                <strong>InvalidHalfLifeError</strong>
                <code>half_life &lt;= 0</code>
              </div>
              <div>
                <span>04</span>
                <strong>ChainDefinitionError</strong>
                <code>bad chain / fractions &gt; 1</code>
              </div>
              <div>
                <span>05</span>
                <strong>DataFormatError</strong>
                <code>broken record / spectra on stable</code>
              </div>
              <div>
                <span>06</span>
                <strong>UnitError</strong>
                <code>bad unit / string on N0 or A0</code>
              </div>
            </div>
            <CodeBlock
              code={`from pydecay import Nuclide, NuclideNotFoundError, PyDecayError\n\ntry:\n    Nuclide.load("Xx-999")\nexcept NuclideNotFoundError:\n    print("Check the spelling, e.g. I-131, Co-60")\n\n# Or catch every pydecay error:\ntry:\n    ...\nexcept PyDecayError as e:\n    print("pydecay said:", e)`}
              label="ERROR HANDLING"
            />

            <h3 className="docs-subhead">
              Unit conversion &amp; decay kernels (7 top-level helpers)
            </h3>
            <p>
              <strong>Use case:</strong> convert activity, atom counts, or times without leaving the{" "}
              <code>pydecay</code> namespace — these are the same functions as{" "}
              <code>pydecay.units</code> / <code>pydecay.decay</code>, re-exported at the package
              root since 0.4.0. Every formula below is exercised live in the{" "}
              <a href="/docs">Unit Converter</a> on the home page.
            </p>
            <CodeBlock
              code={`from pydecay import (\n    to_seconds, bq_to_ci, ci_to_bq,\n    atoms_to_grams, grams_to_atoms,\n    decay_constant, mean_lifetime_s,\n)\n\n# --- time: any unit string → seconds ---\nprint(to_seconds("8.02 days"))   # 692928.0\nprint(to_seconds("6 hours"))     # 21600.0\nprint(to_seconds(692988.48))     # 692988.48 (already seconds)\n\n# --- activity: Bq ↔ Ci (1 Ci = 3.7e10 Bq exactly) ---\nprint(bq_to_ci(3.7e10))          # 1.0\nprint(ci_to_bq(1.0))             # 37000000000.0\nprint(bq_to_ci(1e6))             # 2.7027027e-05  (1 MBq)\n\n# --- mass: atoms ↔ grams (N_A = 6.02214076e23) ---\n# I-131 atomic mass ≈ 130.9061 u\nprint(atoms_to_grams(1e18, 130.9061))  # 0.217478... g\nprint(grams_to_atoms(1.0, 130.9061))   # 4.59775e24 atoms\n\n# --- decay kernels: half-life ↔ λ ↔ τ ---\n# I-131 T½ = 692988.48 s (ICRP-107)\nlam = decay_constant(692988.48)  # 1.000e-6 s⁻¹ (≈ ln2 / T½)\ntau = mean_lifetime_s(lam)       # ≈ 999999.4 s ≈ 11.57 days\nprint(lam, tau)`}
              label="UNIT HELPERS / REAL NUMBERS"
            />
            <div className="docs-rule">
              <span>REAL CALCS</span>
              <p>
                1 MBq = 0.000027027 Ci · 1 g of I-131 = 4.60×10²⁴ atoms · I-131 λ ≈ 1.000×10⁻⁶ s⁻¹ ·
                mean life τ = T½ / ln 2 ≈ 11.57 days. Try the same inputs in the Unit Converter
                playground on the home page.
              </p>
            </div>
            <div className="docs-inline-note">
              <span>TIME</span>
              <strong>to_seconds(t)</strong>
              <span>ACTIVITY</span>
              <strong>bq_to_ci / ci_to_bq</strong>
              <span>MASS</span>
              <strong>atoms_to_grams / grams_to_atoms</strong>
              <span>DECAY</span>
              <strong>decay_constant / mean_lifetime_s</strong>
              <span>RATES</span>
              <strong>dn_dt / da_dt / decay_ode_residual</strong>
            </div>

            <h3 className="docs-subhead">Units — plain numbers or human strings</h3>
            <CodeBlock
              code={`from pydecay import decayed_activity\nimport pint\n\ndecayed_activity(A0=1000.0, half_life="8.02 days", time="24 hours")\ndecayed_activity(A0=1000.0, half_life=692988.48, time=86400.0)  # same, seconds\n\nureg = pint.UnitRegistry()\nn = decayed_activity(A0=1000 * ureg.becquerel, half_life="8.02 days", time="8.02 days")\n# n is still a Quantity in Bq`}
            />
            <div className="docs-rule">
              <span>NOTE</span>
              <p>
                Do not pass strings for <code>N0</code> or <code>A0</code> — use numbers or Pint
                Quantities, or you get <code>UnitError</code>.
              </p>
            </div>

            <h3 className="docs-subhead">Cheat sheet (copy-paste everything)</h3>
            <CodeBlock
              code={`from pydecay import (\n    Nuclide, DecayChain, Inventory,\n    decayed_activity, decayed_atoms, remaining_fraction,\n    emissions, beta_spectrum,\n    to_seconds, bq_to_ci, ci_to_bq,\n    atoms_to_grams, grams_to_atoms,\n    decay_constant, mean_lifetime_s,\n    dn_dt, da_dt, decay_ode_residual,\n    __version__,\n)\n\nprint(__version__)  # \"0.6.0\"\n\ni131 = Nuclide.load("I-131")\nprint(decayed_activity(A0=1000.0, half_life=i131.half_life, time=i131.half_life))  # 500\nprint(remaining_fraction(half_life="8.02 days", time="8.02 days"))  # 0.5\n\nprint(to_seconds("8.02 days"))      # 692928.0\nprint(bq_to_ci(3.7e10))             # 1.0\nprint(atoms_to_grams(1e18, 130.9061))\nprint(decay_constant(692988.48))\n\nprint(dn_dt(1e6, "8.02 days"))      # atoms/s\nprint(da_dt(1000.0, "8.02 days", 0.0))  # Bq/s\nprint(decay_ode_residual(1e6, 8.02 * 86400))  # 0.0\n\nchain = DecayChain.from_isotopes(["Sr-90", "Y-90"])\nprint(chain.at(t="1 day", n0={"Sr-90": 1e6, "Y-90": 0.0}))\n\nb = DecayChain.branching(parent="P", branches={"D1": 0.6, "D2": 0.3},\n                         lambdas={"P": 0.7, "D1": 1e-5, "D2": 2e-5})\nprint(b.at(t=1.0))\n\nrows = emissions("Co-60")\nE, A = beta_spectrum("Sr-90")\nprint(len(rows), len(E))`}
              label="FULL CHEAT SHEET"
            />
            <p className="docs-small-result">
              <span>ONE-LINER</span> Three decay functions answer “how much is left?” ·{" "}
              <code>Nuclide.load</code> looks up 1252 ICRP-107 radionuclides (1498 records with
              stable endpoints) · <code>DecayChain</code> follows parents/daughters ·{" "}
              <code>emissions</code>/<code>beta_spectrum</code> give spectra · seven unit helpers
              convert Bq/Ci, atoms/g, times, and λ/τ · <code>dn_dt</code>/<code>da_dt</code>/
              <code>decay_ode_residual</code> report how fast things change right now.
            </p>
          </DocsSection>

          <DocsSection id="quickstart" number="03" title="Quickstart">
            <p>
              Load a bundled nuclide, compute its activity after one half-life, and find the
              dimensionless fraction remaining after five.
            </p>
            <CodeBlock code={quickstartCode} />
            <p className="docs-small-result">
              <span>EXPECTED RESULT</span> 500 Bq after one half-life; 0.03125 of the initial amount
              after five.
            </p>
          </DocsSection>

          <DocsSection id="single-isotope" number="04" title="Single-isotope decay">
            <p>
              For an isolated isotope, the number of atoms falls exponentially. Activity is the
              decay constant multiplied by the number of undecayed atoms.
            </p>
            <div className="docs-equation">
              <span>THE MODEL</span>
              <div>
                N(t) = N<sub>0</sub>e<sup>-&lambda;t</sup>
              </div>
              <small>
                &lambda; = ln(2) / t<sub>1/2</sub> &nbsp; &middot; &nbsp; A(t) = &lambda;N(t)
              </small>
            </div>
            <p>
              <code>decayed_activity</code> returns activity for the supplied starting activity,
              half-life, and elapsed time. <code>remaining_fraction</code> returns the unitless
              surviving fraction.
            </p>
            <CodeBlock
              code={`from pydecay import Nuclide, decayed_activity, remaining_fraction\n\ni131 = Nuclide.load("I-131")\nactivity = decayed_activity(A0=1000.0, half_life=i131.half_life, time=i131.half_life)\nfraction = remaining_fraction(half_life=i131.half_life, time=5 * i131.half_life)`}
            />
          </DocsSection>

          <DocsSection id="decay-chains" number="05" title="Linear decay chains">
            <p>
              Use <code>DecayChain</code> to evolve populations through a sequence of parent and
              daughter nuclides. A zero decay constant represents a stable endpoint.
            </p>
            <CodeBlock code={chainCode} />
            <p>
              When decay constants are well separated, the solver uses the Bateman closed form. Time
              inputs can be plain values or Pint-style strings such as <code>"1 days"</code>.
            </p>
          </DocsSection>

          <DocsSection id="branching" number="06" title="Branching topologies">
            <p>
              Split a parent into multiple daughters with explicitly defined branch fractions and
              decay constants.
            </p>
            <CodeBlock code={branchingCode} />
            <div className="docs-rule">
              <span>BRANCH RULE</span>
              <p>
                Fractions must add up to no more than 1. In this example, the remaining 10% leaves
                the tracked system as an untracked sink.
              </p>
            </div>
          </DocsSection>

          <DocsSection id="spectra" number="07" title="Radiation spectra">
            <p>
              <code>emissions()</code> returns RAD emission rows (energy, probability, code).{" "}
              <code>beta_spectrum()</code> returns parallel energy/intensity lists for beta
              emitters. Both lazy-load on first call from ICRP-107 RAD/BET artifacts.
            </p>
            <CodeBlock
              code={`from pydecay import emissions, beta_spectrum\n\nrows = emissions("Co-60")       # list of dicts\nE, A = beta_spectrum("Sr-90")  # (energies MeV, intensities)\nprint(len(rows), len(E))`}
            />
            <div className="docs-inline-note">
              <span>RAD</span>
              <strong>emissions(name)</strong>
              <span>BET</span>
              <strong>beta_spectrum(name)</strong>
            </div>
          </DocsSection>

          <DocsSection id="solver" number="08" title="Solver strategy">
            <p>
              pydecay switches methods where the mathematics demands it. The goal is a finite,
              stable answer rather than forcing a fragile closed form.
            </p>
            <div className="docs-strategy">
              <div>
                <span>01 / BATEMAN</span>
                <strong>Well-separated linear chains</strong>
                <p>Use the analytical closed form when decay constants are safely distinct.</p>
              </div>
              <div>
                <span>02 / MATRIX EXPONENTIAL</span>
                <strong>Numerically delicate cases</strong>
                <p>
                  Use <code>scipy.linalg.expm</code> for nearly equal rates, branching, or nonzero
                  daughter initial populations.
                </p>
              </div>
            </div>
            <p>
              Regression tests keep the near-degenerate 0.6931 / 0.6932 case finite and compare the
              two solvers to 1e-10 where both apply.
            </p>
          </DocsSection>

          <DocsSection id="data-units" number="09" title="Nuclide data & units">
            <p>
              The package bundles 1252 ICRP-107 radionuclides (1498 records including stable
              endpoints) with per-record source and fetch date. Lazy-loaded RAD/BET emission yields
              and beta spectra are available via <code>emissions()</code> /{" "}
              <code>beta_spectrum()</code>. This site&apos;s 118-element table is a separate
              reference, not a promise that every isotope is bundled.
            </p>
            <div className="docs-strategy units-strategy">
              <div>
                <span>INTERNAL REPRESENTATION</span>
                <strong>Seconds / atoms / Bq</strong>
                <p>Calculations stay in consistent base quantities.</p>
              </div>
              <div>
                <span>AT THE BOUNDARY</span>
                <strong>Bq &harr; Ci / atoms &harr; grams</strong>
                <p>
                  Top-level <code>bq_to_ci</code>, <code>ci_to_bq</code>,{" "}
                  <code>atoms_to_grams</code>, <code>grams_to_atoms</code>, and{" "}
                  <code>to_seconds</code> (0.4.0).
                </p>
              </div>
            </div>
            <h3 className="docs-subhead">Unit conversion with real numbers</h3>
            <p>
              Internal math never leaves SI (seconds, atoms, becquerels). Convert only at the edge:
            </p>
            <CodeBlock
              code={`from pydecay import bq_to_ci, ci_to_bq, atoms_to_grams, grams_to_atoms, to_seconds, decay_constant, mean_lifetime_s\n\n# Medical source: 1 MBq → Ci\nprint(bq_to_ci(1e6))                 # 2.702702702702703e-05 Ci\n\n# Calibration point: exactly 1 Ci\nprint(ci_to_bq(1.0))                 # 3.7e10 Bq\n\n# I-131 sample: 1e18 atoms, u = 130.9061\nprint(atoms_to_grams(1e18, 130.9061))  # ≈ 0.2175 g\nprint(grams_to_atoms(0.2175, 130.9061))  # ≈ 1.000e18 atoms\n\n# Half-life string → seconds → decay constant\ns = to_seconds("8.02 days")          # 692928.0 s\nprint(decay_constant(s))             # ≈ 1.0000876e-6 1/s\nprint(mean_lifetime_s(decay_constant(s)) / 86400)  # ≈ 8.022 days`}
            />
            <div className="docs-rule">
              <span>EXACT FACTORS</span>
              <p>
                1 Ci = 3.7 × 10¹⁰ Bq (NIST SP 811) · N_A = 6.02214076 × 10²³ mol⁻¹ (exact, 2019 SI)
                · λ = ln(2) / t½ · τ = 1 / λ = t½ / ln 2.
              </p>
            </div>
            <p>
              See the{" "}
              <a
                href="https://www.icrp.org/publications.asp"
                target="_blank"
                rel="noreferrer noopener"
              >
                ICRP publications <ArrowUpRight size={14} />
              </a>{" "}
              and the bundled ICRP-07 data license for the underlying nuclide reference.
            </p>
          </DocsSection>

          <DocsSection id="verification" number="10" title="Verification & next steps">
            <p>
              Worked examples and solver comparisons are part of the project tests. Differential
              checks against radioactivedecay (ICRP-107) report drift and fail past 1e-3 relative
              difference.
            </p>
            <div className="docs-check-list">
              <div>
                <span>01</span>
                <strong>Known I-131 values</strong>
                <code>tests/test_known_values.py</code>
              </div>
              <div>
                <span>02</span>
                <strong>Bateman / expm agreement</strong>
                <code>tests/test_solver.py</code>
              </div>
              <div>
                <span>03</span>
                <strong>External differential check</strong>
                <code>tests/test_crosscheck.py</code>
              </div>
            </div>
            <p>
              For contributors, the quality gates include at least 90% test coverage, static checks,
              and a strict documentation build.
            </p>
            <CodeBlock
              code={`pytest\nruff check src tests\nmypy src\nmkdocs build --strict`}
              label="CONTRIBUTOR CHECKS"
            />
            <p>
              For derivations and solver-dispatch diagrams, continue into the project&apos;s{" "}
              <a href={`${GITHUB_URL}/tree/main/docs`} target="_blank" rel="noreferrer noopener">
                full docs source <ArrowUpRight size={14} />
              </a>
              .
            </p>
            <div className="docs-final-links">
              <a href={GITHUB_URL} target="_blank" rel="noreferrer noopener">
                EXPLORE GITHUB <ArrowUpRight size={16} />
              </a>
              <a href={PYPI_URL} target="_blank" rel="noreferrer noopener">
                VIEW ON PYPI <ArrowUpRight size={16} />
              </a>
            </div>
          </DocsSection>

          <DocsSection id="changelog" number="11" title="Changelog">
            <p>
              Notable changes, Keep a Changelog style. Full detail lives in{" "}
              <a
                href={`${GITHUB_URL}/blob/main/CHANGELOG.md`}
                target="_blank"
                rel="noreferrer noopener"
              >
                CHANGELOG.md <ArrowUpRight size={14} />
              </a>
              .
            </p>
            <div className="changelog-list">
              <article className="changelog-entry is-current">
                <header>
                  <span>0.6.0</span>
                  <time dateTime="2026-09-24">2026-09-24</time>
                </header>
                <h4>Added</h4>
                <ul>
                  <li>
                    Point-source dose rates: <code>dose_rate</code>, <code>exposure_rate</code>,{" "}
                    <code>air_kerma_rate</code>, and <code>Inventory.dose_rate()</code> with curated
                    photon coefficients for 34 nuclides.
                  </li>
                  <li>
                    Narrow-beam shielding: <code>mu_from_material</code>, <code>hvl</code>,{" "}
                    <code>tvl</code>, <code>transmit</code>, <code>hvl_slab</code>,{" "}
                    <code>tvl_slab</code>, <code>transmit_slab</code>,{" "}
                    <code>multilayer_transmit</code> over bundled NIST XCOM tables for seven
                    materials.
                  </li>
                  <li>
                    New exceptions: <code>DoseDataError</code>, <code>MaterialError</code>.
                  </li>
                  <li>Landing page: DOSE and SHIELDING playground tabs.</li>
                </ul>
              </article>
              <article className="changelog-entry">
                <header>
                  <span>0.5.1</span>
                  <time dateTime="2026-09-24">2026-09-24</time>
                </header>
                <h4>Changed</h4>
                <ul>
                  <li>
                    Clarified ICRP-107 catalog counting: 1252 radionuclides + 246 stable endpoints =
                    1498 records (stable endpoints are graph end-caps, not duplicates).
                  </li>
                  <li>
                    Fixed citation label <code>ICRP-07 DATA</code> → <code>ICRP-107 DATA</code> in
                    the docs masthead and footer.
                  </li>
                </ul>
              </article>
              <article className="changelog-entry">
                <header>
                  <span>0.5.0</span>
                  <time dateTime="2026-09-23">2026-09-23</time>
                </header>
                <h4>Added</h4>
                <ul>
                  <li>
                    Instantaneous rates: <code>dn_dt</code>, <code>da_dt</code> (atoms/s, Bq/s)
                    top-level helpers.
                  </li>
                  <li>
                    <code>decay_ode_residual</code> — residual <code>dN/dt + λN</code>; analytic
                    default is exactly 0.
                  </li>
                  <li>
                    Pure kernels <code>pydecay.decay.dn_dt</code> / <code>da_dt</code> /{" "}
                    <code>ode_residual</code>.
                  </li>
                  <li>
                    <code>Inventory.instantaneous_rates()</code> — joint <code>G @ N</code> for the
                    full progeny closure.
                  </li>
                </ul>
              </article>
              <article className="changelog-entry">
                <header>
                  <span>0.4.0</span>
                  <time dateTime="2026-09-23">2026-09-23</time>
                </header>
                <h4>Added</h4>
                <ul>
                  <li>
                    Top-level re-exports: <code>to_seconds</code>, <code>bq_to_ci</code>,{" "}
                    <code>ci_to_bq</code>, <code>atoms_to_grams</code>, <code>grams_to_atoms</code>,{" "}
                    <code>decay_constant</code>, <code>mean_lifetime_s</code> (<code>__all__</code>{" "}
                    16 → 23).
                  </li>
                  <li>Landing page Unit Converter playground with live conversions.</li>
                  <li>Docs: unit-helper section with worked real-number examples.</li>
                </ul>
              </article>
              <article className="changelog-entry">
                <header>
                  <span>0.3.0</span>
                  <time dateTime="2026-09-23">2026-09-23</time>
                </header>
                <h4>Added</h4>
                <ul>
                  <li>
                    Multi-nuclide <code>Inventory</code> with ICRP-107 progeny closure,{" "}
                    <code>cumulative_decays</code>, and <code>decay_time_series</code>.
                  </li>
                  <li>
                    <code>Nuclide.progeny</code> / <code>branching</code> / <code>is_stable</code> /{" "}
                    <code>sf_branch</code>.
                  </li>
                </ul>
                <h4>Changed</h4>
                <ul>
                  <li>Stable nuclides report λ = 0 / activity 0 Bq.</li>
                  <li>
                    <code>decay_time_series</code> argument errors raise <code>PyDecayError</code>.
                  </li>
                  <li>Noisy ICRP branching rows (≤ 1.035) renormalized in closures.</li>
                </ul>
              </article>
              <article className="changelog-entry">
                <header>
                  <span>0.2.0</span>
                  <time dateTime="2026-09-23">2026-09-23</time>
                </header>
                <h4>Added</h4>
                <ul>
                  <li>Full ICRP-107 catalog (1252 radionuclides + 246 stable endpoints).</li>
                  <li>
                    <code>emissions</code> / <code>beta_spectrum</code>.
                  </li>
                </ul>
              </article>
              <article className="changelog-entry">
                <header>
                  <span>0.1.1</span>
                  <time dateTime="2026-09-23">2026-09-23</time>
                </header>
                <h4>Fixed</h4>
                <ul>
                  <li>Package metadata author fields for PyPI.</li>
                </ul>
              </article>
              <article className="changelog-entry">
                <header>
                  <span>0.1.0</span>
                  <time dateTime="2026-09-22">2026-09-22</time>
                </header>
                <h4>Added</h4>
                <ul>
                  <li>
                    Single-isotope analytical decay, <code>DecayChain</code> (Bateman + expm), and
                    spectra access.
                  </li>
                </ul>
              </article>
            </div>
          </DocsSection>
        </article>
      </div>
    </main>
  );
}

function Footer() {
  const nav = useInternalNav();

  return (
    <footer className="site-footer section-shell">
      <div className="footer-top">
        <a href="/" className="footer-brand" onClick={nav("/")}>
          pydecay<span>.</span>
        </a>
        <p>
          Scientific decay mathematics,
          <br />
          made usable.
        </p>
        <div className="footer-links">
          <a href="/docs" onClick={nav("/docs")}>
            DOCUMENTATION <ArrowUpRight size={15} />
          </a>
          <a href={GITHUB_URL} target="_blank" rel="noreferrer noopener">
            GITHUB <ArrowUpRight size={15} />
          </a>
          <a href={PYPI_URL} target="_blank" rel="noreferrer noopener">
            PYPI <ArrowUpRight size={15} />
          </a>
        </div>
      </div>
      <div className="footer-bottom">
        <span>BUILT BY DANIEL DESHMUKH / MIT LICENSE + ICRP-107 DATA (NON-PROFIT)</span>
        <span>
          ELEMENT REFERENCE:{" "}
          <a href="https://periodictableofelements.org" target="_blank" rel="noreferrer noopener">
            PERIODICTABLEOFELEMENTS.ORG
          </a>{" "}
          +{" "}
          <a
            href="https://github.com/andrejewski/periodic-table"
            target="_blank"
            rel="noreferrer noopener"
          >
            PERIODIC-TABLE
          </a>
        </span>
        <span>&copy; PYDECAY</span>
      </div>
    </footer>
  );
}

export default function App() {
  const [path, setPath] = useState(currentPath);
  const isDocs = path === "/docs" || path.startsWith("/docs/");

  useEffect(() => {
    document.title = isDocs
      ? "Documentation | pydecay"
      : "pydecay | Radioactive Decay Mathematics for Python";
  }, [isDocs]);

  useEffect(() => {
    const onPopState = () => setPath(currentPath());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth";
      if (path === "/playground")
        document.getElementById("playground")?.scrollIntoView({ behavior, block: "start" });
      else if (path === "/elements")
        document.getElementById("elements")?.scrollIntoView({ behavior, block: "start" });
      else if (path.startsWith("/docs/"))
        document
          .getElementById(path.slice("/docs/".length))
          ?.scrollIntoView({ behavior, block: "start" });
      else window.scrollTo({ top: 0, behavior: "auto" });
    }, 30);
    return () => window.clearTimeout(timeout);
  }, [path]);

  return (
    <MotionConfig reducedMotion="user">
      <SiteHeader path={path} />
      {isDocs ? <DocsPage path={path} /> : <HomePage />}
      <Footer />
    </MotionConfig>
  );
}

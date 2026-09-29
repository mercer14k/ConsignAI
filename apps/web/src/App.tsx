import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowLeftRight,
  ArrowRight,
  Box,
  Boxes,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Clock3,
  Database,
  FileCheck2,
  GitBranch,
  Layers3,
  LayoutDashboard,
  LoaderCircle,
  LockKeyhole,
  Menu,
  Package,
  Play,
  Search,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  Upload,
  X,
} from "lucide-react";
import {
  api,
  ApiError,
  exportCsv,
  label,
  money,
  number,
  setCredentials,
} from "./api";
import { StockChart } from "./Chart";
import { LocalModelPicker } from "./LocalModelPicker";
import type {
  Alert,
  Batch,
  Evidence,
  Overview,
  Page,
  Position,
  Transfer,
  View,
} from "./types";

const views: View[] = [
  "Overview",
  "Exceptions",
  "Inventory",
  "Redistribution",
  "Data & imports",
  "Architecture",
];
const icons = [
  LayoutDashboard,
  TriangleAlert,
  Boxes,
  ArrowLeftRight,
  Database,
  GitBranch,
];
const categoryShort: Record<string, string> = {
  "Fiber & cable": "Fiber",
  "Network hardware": "Network",
  "Power systems": "Power",
  "Site materials": "Site",
  "Safety & tools": "Safety",
};
function Badge({
  children,
  tone = "muted",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
function Empty({ title, description }: { title: string; description: string }) {
  return (
    <div className="empty">
      <FileCheck2 size={28} />
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
function Modal({
  children,
  onClose,
  title,
  wide = false,
}: {
  children: React.ReactNode;
  onClose: () => void;
  title: string;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = ref.current;
    el?.showModal();
    return () => el?.close();
  }, []);
  return (
    <dialog
      className={wide ? "drawer" : "modal"}
      ref={ref}
      onCancel={onClose}
      aria-label={title}
    >
      <header className="dialog-head">
        <div>
          <span className="eyebrow">CONSIGNAI WORKSPACE</span>
          <h2>{title}</h2>
        </div>
        <button
          className="icon-button"
          aria-label="Close panel"
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </header>
      {children}
    </dialog>
  );
}

export default function App() {
  const [view, setView] = useState<View>(
    () =>
      views.find((v) => v === decodeURIComponent(location.hash.slice(1))) ||
      "Overview",
  );
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [mobile, setMobile] = useState(false);
  const [q, setQ] = useState("");
  const [market, setMarket] = useState("");
  const [kind, setKind] = useState("");
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [alerts, setAlerts] = useState<Page<Alert>>({
    items: [],
    total: 0,
    limit: 25,
    offset: 0,
  });
  const [positions, setPositions] = useState<Page<Position>>({
    items: [],
    total: 0,
    limit: 25,
    offset: 0,
  });
  const [transfers, setTransfers] = useState<Page<Transfer>>({
    items: [],
    total: 0,
    limit: 25,
    offset: 0,
  });
  const [batches, setBatches] = useState<Batch[]>([]);
  const [selected, setSelected] = useState<{
    location: string;
    sku: string;
  } | null>(null);
  const [notice, setNotice] = useState("");
  const [auth, setAuth] = useState(false);
  const [modelPicker, setModelPicker] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [read, setRead] = useState("");
  const [write, setWrite] = useState("");
  const [meta, setMeta] = useState<{
    mode: string;
    ai_runtime: string;
    weekly_jobs: boolean;
  } | null>(null);
  const reload = useCallback(async () => {
    try {
      const [o, m] = await Promise.all([
        api<Overview>("/overview").catch((e) => {
          if (e instanceof ApiError && e.status === 404) return null;
          throw e;
        }),
        api<{ mode: string; ai_runtime: string; weekly_jobs: boolean }>(
          "/meta",
        ),
      ]);
      setOverview(o);
      setMeta(m);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    void reload();
  }, [reload, revision]);
  const navigate = (v: View) => {
    setView(v);
    location.hash = v;
    setQ("");
    setKind("");
    setOffset(0);
    setMobile(false);
  };
  useEffect(() => {
    const handler = () => {
      const v = views.find(
        (v) => v === decodeURIComponent(location.hash.slice(1)),
      );
      if (v) setView(v);
    };
    window.addEventListener("hashchange", handler);
    return () => window.removeEventListener("hashchange", handler);
  }, []);
  useEffect(() => {
    if (!overview && !meta) return;
    let active = true;
    setLoading(true);
    const params = new URLSearchParams({
      q,
      market,
      kind,
      offset: String(offset),
      limit: "25",
      ...(overview ? { run_id: overview.id } : {}),
    });
    const collection = !overview
      ? "batches"
      : view === "Inventory"
        ? "positions"
        : view === "Redistribution"
          ? "transfers"
          : view === "Data & imports"
            ? "batches"
            : "alerts";
    const timer = window.setTimeout(() => {
      api<Page<any>>(`/${collection}?${params}`)
        .then((data) => {
          if (!active) return;
          if (collection === "positions") setPositions(data);
          else if (collection === "transfers") setTransfers(data);
          else if (collection === "batches") setBatches(data.items);
          else setAlerts(data);
          setError("");
        })
        .catch((e) => {
          if (active) setError(e.message);
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, 150);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [view, q, market, kind, offset, overview, meta, revision]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 7000);
    return () => clearTimeout(timer);
  }, [notice]);
  const run = async () => {
    setBusy(true);
    try {
      await api("/commands/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: "{}",
      });
      setRevision((r) => r + 1);
      setNotice(
        "Analysis complete. All results are linked to a new immutable run.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const doExport = async () => {
    try {
      await exportCsv(
        new URLSearchParams({ q, market, kind, run_id: overview?.id || "" }),
      );
      setNotice("Exception list exported.");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const openPosition = (p: { location_id: string; sku: string }) =>
    setSelected({ location: p.location_id, sku: p.sku });
  const summary = overview?.summary;
  const activePage =
    view === "Inventory"
      ? positions
      : view === "Redistribution"
        ? transfers
        : alerts;
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className={`sidebar ${mobile ? "mobile-open" : ""}`}>
        <a
          className="brand"
          href="#Overview"
          onClick={() => navigate("Overview")}
        >
          <span className="brand-icon">
            <Box size={23} strokeWidth={2.2} />
          </span>
          Consign<span>AI</span>
        </a>
        <div className="workspace">
          <span className="workspace-avatar">CN</span>
          <div>
            ConsignAI Network<small>Inventory operations</small>
          </div>
          <ChevronDown size={15} />
        </div>
        <span className="nav-label">WORKSPACE</span>
        <nav aria-label="Main navigation">
          {views.map((v, i) => {
            const Icon = icons[i];
            return (
              <button
                key={v}
                className={view === v ? "nav-item active" : "nav-item"}
                onClick={() => navigate(v)}
                aria-current={view === v ? "page" : undefined}
              >
                <Icon size={18} />
                <span>{v}</span>
                {v === "Exceptions" && summary ? (
                  <span className="nav-count">{summary.exception_count}</span>
                ) : null}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-card">
            <ShieldCheck size={20} />
            <strong>Local by design</strong>
            <p>
              Your inventory. Your machine.
              <br />
              No cloud AI required.
            </p>
            <Badge tone={selectedModel ? "purple" : "green"}>
              {selectedModel ? "Local AI selected" : "No model selected"}
            </Badge>
            {selectedModel && (
              <span className="selected-model-name">{selectedModel}</span>
            )}
            <button
              className="secondary model-picker-button"
              onClick={() => {
                setMobile(false);
                setModelPicker(true);
              }}
            >
              <Sparkles size={14} />
              {selectedModel ? "Change AI model" : "Select AI model"}
            </button>
          </div>
          <button className="profile" onClick={() => setAuth(true)}>
            <span className="avatar">OP</span>
            <span>
              Operations workspace
              <small>
                {meta?.mode === "secured"
                  ? "Secured access"
                  : "Local demo access"}
              </small>
            </span>
            <LockKeyhole size={15} />
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              aria-label="Open navigation"
              className="icon-button mobile-toggle"
              onClick={() => setMobile(!mobile)}
            >
              <Menu size={20} />
            </button>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{view}</strong>
          </div>
          <div className="topbar-right">
            <Badge tone="green">
              <span className="status-dot" />
              {summary ? "Local dataset" : "No analysis yet"}
            </Badge>
            <span className="divider" />
            <span className="local-status">
              <LockKeyhole size={14} /> Local environment
            </span>
          </div>
        </header>
        <main id="main">
          <div className="page-header">
            <div>
              <div className="eyebrow">DISTRIBUTED INVENTORY INTELLIGENCE</div>
              <h1>
                {view === "Overview"
                  ? "Every unit. Accounted for."
                  : view === "Exceptions"
                    ? "Find the signal. Follow the evidence."
                    : view === "Inventory"
                      ? "One network. Every stock position."
                      : view === "Redistribution"
                        ? "Put stranded stock to work."
                        : view === "Data & imports"
                          ? "Good decisions start with good data."
                          : "Built to be inspected."}
              </h1>
              <p>
                {view === "Overview"
                  ? "See what’s at risk, what’s sitting idle, and where stock needs to go."
                  : view === "Exceptions"
                    ? "Prioritized exceptions with the records behind every finding."
                    : view === "Inventory"
                      ? "Reported counts, ledger expectations, and consumption-based coverage."
                      : view === "Redistribution"
                        ? "Review proposals that respect ownership, capacity, and protected stock."
                        : view === "Data & imports"
                          ? "Validated, traceable imports. Invalid batches never partially change inventory."
                          : "Deterministic accounting at the center. Local AI at the edge."}
              </p>
            </div>
            <button className="primary" onClick={run} disabled={busy}>
              {busy ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                <Play size={15} />
              )}{" "}
              {busy ? "Analyzing…" : "Run analysis"}
            </button>
          </div>
          {error && (
            <div role="alert" className="error-banner">
              <TriangleAlert size={18} />
              <span>{error}</span>
              <button
                onClick={() => {
                  void reload();
                  setRevision((r) => r + 1);
                }}
              >
                Retry
              </button>
              {error.includes("authorization") && (
                <button onClick={() => setAuth(true)}>Enter credentials</button>
              )}
            </div>
          )}
          {!overview && !meta && !error ? (
            <div className="initial-loading">
              <LoaderCircle className="spin" />
              <h2>Connecting to your inventory network</h2>
              <p>
                The first launch generates and validates a full year of
                synthetic data.
              </p>
            </div>
          ) : null}
          {!overview && meta && (
            <>
              <div className="warning-banner">
                Start your workspace: import catalogs and stock evidence below,
                then run analysis. No demo data is required.
              </div>
              <DataPanel
                batches={batches}
                refreshed={() => setRevision((r) => r + 1)}
                fail={setError}
              />
            </>
          )}
          {overview && summary && (
            <>
              <div className="context-bar">
                <div>
                  <span className="tiny-square" />
                  Network overview <span className="context-sep">/</span>
                  <strong>{number(summary.contractors)} contractors</strong>
                  <span className="context-sep">/</span>
                  {number(summary.skus)} materials
                </div>
                <div>
                  <Clock3 size={14} /> As of{" "}
                  {new Date(overview.as_of + "T12:00:00").toLocaleDateString(
                    "en-US",
                    { month: "short", day: "numeric", year: "numeric" },
                  )}
                  <Badge>Computed</Badge>
                </div>
              </div>
              {overview.stale_analysis && (
                <div className="warning-banner">
                  New data has been imported. Run analysis to update these
                  results.
                </div>
              )}
              {view === "Overview" && (
                <>
                  <section
                    className="metrics"
                    aria-label="Key inventory metrics"
                  >
                    <Metric
                      title="Inventory under management"
                      value={money(summary.inventory_value_cents, true)}
                      note={`${number(summary.positions)} reported stock positions`}
                      icon={<Package size={19} />}
                      spark="normal"
                    />
                    <Metric
                      title="Unexplained variance"
                      value={money(summary.variance_value_cents)}
                      note="Absolute difference from the ledger"
                      icon={<Activity size={19} />}
                      tone="amber"
                      spark="amber"
                    />
                    <Metric
                      title="Positions facing shortage"
                      value={String(summary.shortage_count).padStart(2, "0")}
                      note="Available coverage below lead time"
                      icon={<TriangleAlert size={19} />}
                      tone="red"
                    />
                    <Metric
                      title="Redistribution candidates"
                      value={money(summary.redistribution_value_cents, true)}
                      note="Stock value in constrained proposals"
                      icon={<ArrowLeftRight size={19} />}
                      tone="lime"
                    />
                  </section>
                  <div className="overview-grid">
                    <section className="panel trend-panel">
                      <div className="panel-heading">
                        <div>
                          <h2>
                            Inventory in motion <Badge>Raw snapshots</Badge>
                          </h2>
                          <p>Reported on-hand value across the network</p>
                        </div>
                        <Badge>Last {overview.trend.length} days</Badge>
                      </div>
                      <StockChart trend={overview.trend} />
                      <div className="chart-footer">
                        <span>
                          <i className="legend-line" />
                          Reported stock value
                        </span>
                        <span>USD · standard material cost</span>
                      </div>
                    </section>
                    <section className="panel pulse-panel">
                      <div className="panel-heading">
                        <div>
                          <h2>Network pulse</h2>
                          <p>Exceptions by detection rule</p>
                        </div>
                        <Activity size={18} />
                      </div>
                      <div className="pulse-total">
                        {summary.exception_count}
                        <span>open exceptions</span>
                        <Badge tone="amber">Needs review</Badge>
                      </div>
                      <div className="stacked-bar">
                        {Object.entries(summary.anomaly_counts).map(
                          ([k, v], i) => (
                            <span
                              key={k}
                              style={{
                                flex: v,
                                background: [
                                  "#f19b70",
                                  "#c4f176",
                                  "#a18bdb",
                                  "#6ca9da",
                                  "#e5c579",
                                  "#d6707c",
                                ][i % 6],
                              }}
                              title={`${label(k)}: ${v}`}
                            />
                          ),
                        )}
                      </div>
                      <div className="pulse-list">
                        {Object.entries(summary.anomaly_counts).map(
                          ([k, v], i) => (
                            <button
                              key={k}
                              onClick={() => {
                                navigate("Exceptions");
                                setKind(k);
                              }}
                            >
                              <span>
                                <i
                                  style={{
                                    background: [
                                      "#f19b70",
                                      "#c4f176",
                                      "#a18bdb",
                                      "#6ca9da",
                                      "#e5c579",
                                      "#d6707c",
                                    ][i % 6],
                                  }}
                                />
                                {label(k)}
                              </span>
                              <strong>
                                {v}
                                <ChevronRight size={14} />
                              </strong>
                            </button>
                          ),
                        )}
                      </div>
                    </section>
                  </div>
                  <div className="bottom-grid">
                    <section className="panel exception-panel">
                      <div className="panel-heading">
                        <div>
                          <h2>
                            Attention required{" "}
                            <span className="count-chip">
                              {summary.exception_count}
                            </span>
                          </h2>
                          <p>Highest-priority exceptions across your network</p>
                        </div>
                        <button
                          className="text-button"
                          onClick={() => navigate("Exceptions")}
                        >
                          View all <ArrowRight size={15} />
                        </button>
                      </div>
                      <AlertTable
                        alerts={alerts.items.slice(0, 5)}
                        open={openPosition}
                        compact
                      />
                    </section>
                    <section className="panel heatmap-panel">
                      <div className="panel-heading">
                        <div>
                          <h2>Risk by market</h2>
                          <p>Summed position risk · select to investigate</p>
                        </div>
                      </div>
                      <div className="heatmap">
                        <div className="heatmap-row">
                          <span />
                          {Object.values(categoryShort).map((c) => (
                            <span className="heatmap-col" key={c}>
                              {c}
                            </span>
                          ))}
                        </div>
                        {overview.markets.map((m) => (
                          <div className="heatmap-row" key={m.market}>
                            <span className="market-label">{m.market}</span>
                            {Object.keys(categoryShort).map((c) => {
                              const n = m.categories[c] || 0;
                              return (
                                <button
                                  className={`heat heat-${n === 0 ? 0 : n < 100 ? 1 : n < 250 ? 2 : 3}`}
                                  key={c}
                                  aria-label={`${m.market}, ${c}: risk score ${n}`}
                                  title={`${c}: ${n} cumulative risk`}
                                  onClick={() => {
                                    navigate("Exceptions");
                                    setMarket(m.market);
                                    setQ(c);
                                  }}
                                >
                                  {n}
                                </button>
                              );
                            })}
                          </div>
                        ))}
                      </div>
                      <div className="heat-legend">
                        <span>Lower risk</span>
                        {[0, 1, 2, 3].map((i) => (
                          <i key={i} className={`heat-${i}`} />
                        ))}
                        <span>Higher risk</span>
                      </div>
                    </section>
                  </div>
                  <div className="provenance-footer">
                    <ShieldCheck size={15} />
                    <span>
                      Every metric is computed from imported evidence.
                    </span>
                    <span>
                      {number(summary.record_count)} records · Run{" "}
                      {overview.id.slice(0, 8)} · {summary.elapsed_seconds}s
                    </span>
                  </div>
                </>
              )}
              {view === "Inventory" && (
                <section className="panel contractor-matrix">
                  <div className="panel-heading">
                    <div>
                      <h2>
                        Coverage across markets <Badge>Prediction</Badge>
                      </h2>
                      <p>
                        Available units divided by estimated daily consumption
                        across eligible positions
                      </p>
                    </div>
                  </div>
                  <div className="market-coverage">
                    {overview.markets.map((m) => (
                      <div key={m.market}>
                        <span>{m.market}</span>
                        <strong>
                          {m.days_of_supply == null
                            ? "—"
                            : m.days_of_supply + "d"}
                        </strong>
                      </div>
                    ))}
                  </div>
                  <details>
                    <summary>
                      Contractor / material risk matrix · highest aggregate risk
                      first
                    </summary>
                    <div className="contractor-risk-rows">
                      {(overview.contractors || [])
                        .filter((c) => !market || c.market === market)
                        .slice(0, 10)
                        .map((c) => (
                          <div
                            className="contractor-risk-row"
                            key={c.location_id}
                          >
                            <span>
                              {c.location_name}
                              <small>
                                {c.market} ·{" "}
                                {c.days_of_supply == null
                                  ? "No estimate"
                                  : c.days_of_supply + "d coverage"}
                              </small>
                            </span>
                            <div>
                              {c.materials.map((m) => (
                                <button
                                  className={`heat heat-${m.risk_score === 0 ? 0 : m.risk_score < 30 ? 1 : m.risk_score < 50 ? 2 : 3}`}
                                  key={m.sku}
                                  title={`${m.name}: risk ${m.risk_score}`}
                                  aria-label={`Inspect ${c.location_name} ${m.name}, risk ${m.risk_score}`}
                                  onClick={() =>
                                    setSelected({
                                      location: c.location_id,
                                      sku: m.sku,
                                    })
                                  }
                                >
                                  {m.sku}
                                  <b>{m.risk_score}</b>
                                </button>
                              ))}
                            </div>
                          </div>
                        ))}
                    </div>
                  </details>
                </section>
              )}
              {(view === "Exceptions" ||
                view === "Inventory" ||
                view === "Redistribution") && (
                <section className="panel full-panel">
                  <div className="filters">
                    <div className="search-box">
                      <Search size={17} />
                      <input
                        aria-label="Search records"
                        placeholder="Search material, contractor, or market…"
                        value={q}
                        onChange={(e) => {
                          setQ(e.target.value);
                          setOffset(0);
                        }}
                      />
                      {q && (
                        <button
                          aria-label="Clear search"
                          onClick={() => setQ("")}
                        >
                          <X size={14} />
                        </button>
                      )}
                    </div>
                    <select
                      aria-label="Filter market"
                      value={market}
                      onChange={(e) => {
                        setMarket(e.target.value);
                        setOffset(0);
                      }}
                    >
                      <option value="">All markets</option>
                      {overview.markets.map((m) => (
                        <option key={m.market}>{m.market}</option>
                      ))}
                    </select>
                    {view === "Exceptions" && (
                      <select
                        aria-label="Filter exception type"
                        value={kind}
                        onChange={(e) => {
                          setKind(e.target.value);
                          setOffset(0);
                        }}
                      >
                        <option value="">All exceptions</option>
                        {Object.keys(summary.anomaly_counts).map((k) => (
                          <option key={k} value={k}>
                            {label(k)}
                          </option>
                        ))}
                      </select>
                    )}
                    {view === "Exceptions" && (
                      <button className="secondary" onClick={doExport}>
                        <ArrowDownToLine size={16} />
                        Export CSV
                      </button>
                    )}
                    <span className="result-count">
                      {loading ? (
                        <LoaderCircle className="spin" size={16} />
                      ) : (
                        number(activePage.total) + " results"
                      )}
                    </span>
                  </div>
                  {view === "Exceptions" && (
                    <AlertTable alerts={alerts.items} open={openPosition} />
                  )}
                  {view === "Inventory" && (
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Material / location</th>
                            <th>Market</th>
                            <th>Reported</th>
                            <th>Expected</th>
                            <th>Variance</th>
                            <th>
                              Available supply <Badge>Prediction</Badge>
                            </th>
                            <th>Risk</th>
                          </tr>
                        </thead>
                        <tbody>
                          {positions.items.map((p) => (
                            <tr key={p.location_id + p.sku}>
                              <td>
                                <button
                                  className="cell-link"
                                  onClick={() => openPosition(p)}
                                >
                                  {p.material_name}
                                  <small>
                                    {p.location_name} · {p.sku}
                                  </small>
                                </button>
                              </td>
                              <td>{p.market}</td>
                              <td className="mono">
                                {number(p.on_hand)} <small>{p.unit}</small>
                              </td>
                              <td className="mono">{number(p.expected)}</td>
                              <td
                                className={
                                  p.variance
                                    ? "text-red mono"
                                    : "text-muted mono"
                                }
                              >
                                {p.variance > 0 ? "+" : ""}
                                {p.variance}
                              </td>
                              <td>
                                {p.days_of_supply === null ? (
                                  <span className="text-muted">
                                    Not estimated
                                  </span>
                                ) : (
                                  <Badge
                                    tone={
                                      p.days_of_supply < 7 ? "red" : "green"
                                    }
                                  >
                                    {p.days_of_supply.toFixed(1)} days
                                  </Badge>
                                )}
                              </td>
                              <td>
                                <Badge
                                  tone={
                                    p.risk_score >= 50
                                      ? "red"
                                      : p.risk_score
                                        ? "amber"
                                        : "muted"
                                  }
                                >
                                  {p.risk_score
                                    ? `${p.risk_score} / 100`
                                    : "Clear"}
                                </Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {view === "Redistribution" && (
                    <>
                      <div className="proposal-note">
                        <ShieldCheck size={17} />
                        Proposals only. Operations must verify physical stock
                        and authorize each transfer. No inventory is moved
                        automatically.
                      </div>
                      <div className="transfer-grid">
                        {transfers.items.map((t) => (
                          <article className="transfer-card" key={t.id}>
                            <div className="transfer-top">
                              <Badge tone="green">{t.market}</Badge>
                              <span className="mono">
                                {t.quantity} {t.unit}
                              </span>
                            </div>
                            <h3>{t.material_name}</h3>
                            <div className="transfer-route">
                              <button
                                onClick={() =>
                                  setSelected({
                                    location: t.from_location,
                                    sku: t.sku,
                                  })
                                }
                              >
                                {t.from_name}
                                <small>Origin</small>
                              </button>
                              <ArrowRight size={19} />
                              <button
                                onClick={() =>
                                  setSelected({
                                    location: t.to_location,
                                    sku: t.sku,
                                  })
                                }
                              >
                                {t.to_name}
                                <small>Destination</small>
                              </button>
                            </div>
                            <div className="coverage">
                              <span>Available coverage</span>
                              <strong>
                                {t.coverage_before}d <ArrowRight size={14} />{" "}
                                <span>{t.coverage_after}d</span>
                              </strong>
                            </div>
                            <div className="constraints">
                              {t.constraints.map((c) => (
                                <span key={c}>
                                  <Check size={12} />
                                  {c}
                                </span>
                              ))}
                            </div>
                            {t.expedite_required && (
                              <p className="text-amber">
                                Expedite: coverage is shorter than the two-day
                                transfer lead time.
                              </p>
                            )}
                            <div className="transfer-bottom">
                              <span>Stock value</span>
                              <strong>{money(t.value_cents)}</strong>
                            </div>
                          </article>
                        ))}
                      </div>
                    </>
                  )}
                  {!loading && activePage.total === 0 && (
                    <Empty
                      title="No matching records"
                      description="Try a different search or clear your filters."
                    />
                  )}
                  <div className="pagination">
                    <span>
                      Showing {activePage.total ? offset + 1 : 0}–
                      {Math.min(offset + 25, activePage.total)} of{" "}
                      {number(activePage.total)}
                    </span>
                    <div>
                      <button
                        aria-label="Previous page"
                        disabled={offset === 0}
                        onClick={() => setOffset(Math.max(0, offset - 25))}
                      >
                        <ChevronLeft size={16} />
                      </button>
                      <button
                        aria-label="Next page"
                        disabled={offset + 25 >= activePage.total}
                        onClick={() => setOffset(offset + 25)}
                      >
                        <ChevronRight size={16} />
                      </button>
                    </div>
                  </div>
                </section>
              )}
              {view === "Data & imports" && (
                <DataPanel
                  batches={batches}
                  summary={summary}
                  refreshed={() => setRevision((r) => r + 1)}
                  fail={setError}
                />
              )}
              {view === "Architecture" && (
                <Architecture
                  overview={overview}
                  meta={meta}
                  selectedModel={selectedModel}
                />
              )}
            </>
          )}
        </main>
        <footer className="app-footer">
          <span>
            CONSIGNAI <b>/</b> Evidence before intelligence.
          </span>
          <span>Open source · Local first · v0.1.0</span>
        </footer>
      </div>
      {notice && (
        <div className="toast" role="status">
          <Check size={17} />
          {notice}
          <button
            aria-label="Dismiss notification"
            onClick={() => setNotice("")}
          >
            <X size={14} />
          </button>
        </div>
      )}
      {selected && overview && (
        <EvidencePanel
          key={`${selected.location}:${selected.sku}:${overview.id}:${selectedModel || "none"}`}
          selected={selected}
          runId={overview.id}
          selectedModel={selectedModel}
          onClose={() => setSelected(null)}
        />
      )}
      {modelPicker && (
        <Modal
          title="Select a local AI model"
          onClose={() => setModelPicker(false)}
        >
          <LocalModelPicker
            selected={selectedModel}
            onSelect={(model) => {
              setSelectedModel(model);
              setModelPicker(false);
              setNotice(
                model
                  ? `Local model selected: ${model}`
                  : "AI disabled. Computed briefs remain available.",
              );
            }}
          />
        </Modal>
      )}
      {auth && (
        <Modal onClose={() => setAuth(false)} title="Workspace credentials">
          <form
            className="auth-form"
            onSubmit={(e) => {
              e.preventDefault();
              setCredentials(read, write);
              setAuth(false);
              setRevision((r) => r + 1);
            }}
          >
            <p>
              Only needed for secured deployments. Credentials stay in memory
              and are cleared on refresh.
            </p>
            <label>
              Read bearer token
              <input
                type="password"
                value={read}
                onChange={(e) => setRead(e.target.value)}
                autoComplete="off"
              />
            </label>
            <label>
              Write API key
              <input
                type="password"
                value={write}
                onChange={(e) => setWrite(e.target.value)}
                autoComplete="off"
              />
            </label>
            <button className="primary">Apply credentials</button>
          </form>
        </Modal>
      )}
    </div>
  );
}

function Metric({
  title,
  value,
  note,
  icon,
  tone = "",
  spark,
}: {
  title: string;
  value: string;
  note: string;
  icon: React.ReactNode;
  tone?: string;
  spark?: string;
}) {
  return (
    <article className={`metric ${tone}`}>
      <div className="metric-label">
        {title}
        <span>{icon}</span>
      </div>
      <div className="metric-value">
        {value}
        {spark && (
          <span className={`metric-mark ${spark}`} aria-hidden="true">
            {spark === "amber" ? (
              <Activity size={44} strokeWidth={1} />
            ) : (
              <Layers3 size={39} strokeWidth={1} />
            )}
          </span>
        )}
      </div>
      <p>{note}</p>
    </article>
  );
}
function AlertTable({
  alerts,
  open,
  compact = false,
}: {
  alerts: Alert[];
  open: (a: Alert) => void;
  compact?: boolean;
}) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Contractor / material</th>
            <th>Exception</th>
            {!compact && <th>Market</th>}
            <th>Priority</th>
            <th className="align-right">
              {compact ? "Variance / coverage" : "Stock exposure"}
            </th>
            <th>
              <span className="sr-only">Action</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((a) => (
            <tr key={a.id}>
              <td>
                <button className="cell-link" onClick={() => open(a)}>
                  {a.location_name}
                  <small>{a.material_name}</small>
                </button>
              </td>
              <td>
                <span className="exception-kind">{label(a.kind)}</span>
              </td>
              {!compact && <td>{a.market}</td>}
              <td>
                <Badge
                  tone={
                    a.severity === "critical"
                      ? "red"
                      : a.severity === "high"
                        ? "amber"
                        : "muted"
                  }
                >
                  {a.severity}
                </Badge>
              </td>
              <td className="align-right mono">
                {compact
                  ? a.kind === "variance"
                    ? `${a.variance > 0 ? "+" : ""}${a.variance} ${a.unit}`
                    : a.days_of_supply !== null
                      ? `${a.days_of_supply.toFixed(1)}d`
                      : "—"
                  : money(a.value_cents)}
              </td>
              <td>
                <button
                  className="icon-button row-open"
                  aria-label={`Inspect ${a.location_name} ${a.material_name}`}
                  onClick={() => open(a)}
                >
                  <ArrowRight size={15} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EvidencePanel({
  selected,
  runId,
  selectedModel,
  onClose,
}: {
  selected: { location: string; sku: string };
  runId: string;
  selectedModel: string | null;
  onClose: () => void;
}) {
  const [data, setData] = useState<Evidence | null>(null);
  const [error, setError] = useState("");
  const [offset, setOffset] = useState(0);
  const [explanation, setExplanation] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    api<Evidence>(
      `/evidence/${selected.location}/${selected.sku}?run_id=${runId}&offset=${offset}&limit=25`,
    )
      .then((d) => {
        if (active) setData(d);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [selected, runId, offset]);
  const narrate = async () => {
    if (!data?.alerts[0]) return;
    setBusy(true);
    setError("");
    setExplanation(null);
    try {
      setExplanation(
        await api(
          `/commands/explain/${encodeURIComponent(data.alerts[0].id)}?run_id=${runId}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model: selectedModel }),
          },
        ),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const p = data?.position;
  return (
    <Modal
      wide
      onClose={onClose}
      title={p?.location_name || "Loading evidence…"}
    >
      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}
      {p && data ? (
        <div className="evidence-content">
          <div className="evidence-material">
            <span className="material-icon">
              <Package size={25} />
            </span>
            <div>
              <h3>{p.material_name}</h3>
              <p>
                {p.sku} · {p.market} · {p.unit}
              </p>
            </div>
            <Badge>Raw + computed</Badge>
          </div>
          <section className="equation">
            <div>
              <span>Opening count</span>
              <strong>{p.opening}</strong>
              <small>{p.opening_day}</small>
            </div>
            <b>+</b>
            <div>
              <span>Net movements</span>
              <strong>
                {p.net_movement > 0 ? "+" : ""}
                {p.net_movement}
              </strong>
              <small>{number(p.movement_count)} records</small>
            </div>
            <b>=</b>
            <div>
              <span>Expected</span>
              <strong>{p.expected}</strong>
              <small>Ledger balance</small>
            </div>
          </section>
          <div className="count-comparison">
            <div>
              Reported on hand
              <strong>
                {p.on_hand} <small>{p.unit}</small>
              </strong>
            </div>
            <div>
              Unexplained variance
              <strong className={p.variance ? "text-red" : "text-lime"}>
                {p.variance > 0 ? "+" : ""}
                {p.variance} <small>{p.unit}</small>
              </strong>
            </div>
          </div>
          <p className="evidence-caption">
            Reconciled through {p.snapshot_day}. Opening stock is the accounting
            baseline. Variance indicates a discrepancy, not proof of shrinkage.
          </p>
          <div className="evidence-section">
            <h3>
              Findings <Badge>Computed</Badge>
            </h3>
            {data.alerts.length ? (
              data.alerts.map((a) => (
                <article className="finding" key={a.id}>
                  <div>
                    <Badge tone={a.severity === "critical" ? "red" : "amber"}>
                      {a.severity}
                    </Badge>
                    <strong>{a.title}</strong>
                  </div>
                  <p>{a.detail}</p>
                </article>
              ))
            ) : (
              <p>No rule-based exceptions for this position.</p>
            )}
          </div>
          <div className="forecast-card">
            <div>
              <h3>
                Available days of supply <Badge>Prediction</Badge>
              </h3>
              <p>
                {p.daily_demand === null
                  ? "Insufficient history, missing counts, or warehouse position."
                  : `${p.available} available units ÷ ${p.daily_demand.toFixed(2)} estimated daily consumption`}
              </p>
            </div>
            <strong>
              {p.days_of_supply === null
                ? "—"
                : p.days_of_supply.toFixed(1) + "d"}
            </strong>
          </div>
          <p className="evidence-caption">
            {label(p.method)} · {label(p.forecast_quality)}. Consumption is a
            proxy for demand, not a project schedule.
          </p>
          <div className="evidence-section">
            <div className="section-line">
              <h3>Evidence brief</h3>
              <button
                className="secondary"
                onClick={narrate}
                disabled={busy || !data.alerts.length}
              >
                {busy ? (
                  <LoaderCircle size={15} className="spin" />
                ) : (
                  <Sparkles size={15} />
                )}
                Explain finding
              </button>
            </div>
            <p className="evidence-caption">
              {selectedModel
                ? `Selected local model: ${selectedModel}`
                : "No model selected · computed brief"}
            </p>
            {explanation ? (
              <div className="narrative">
                <Badge
                  tone={explanation.mode === "local_ai" ? "purple" : "green"}
                >
                  {explanation.mode === "local_ai"
                    ? "AI-selected brief"
                    : label(explanation.mode)}
                </Badge>
                {explanation.mode === "deterministic_fallback" && (
                  <p className="text-amber">
                    The selected model could not produce a valid local brief.
                    Showing the computed explanation; no other model was used.
                  </p>
                )}
                {explanation.telemetry.model && (
                  <p className="evidence-caption">
                    Requested model: {explanation.telemetry.model}
                  </p>
                )}
                <p>{explanation.explanation.summary}</p>
                <strong>
                  Next action: {label(explanation.explanation.next_action)}
                </strong>
                <details>
                  <summary>
                    Supporting record IDs (
                    {explanation.explanation.evidence_ids.length})
                  </summary>
                  {explanation.explanation.evidence_ids.map((id: string) => (
                    <code key={id}>{id}</code>
                  ))}
                </details>
              </div>
            ) : (
              <p className="text-muted">
                Request an evidence-linked explanation. The deterministic brief
                works without a local model.
              </p>
            )}
          </div>
          <div className="evidence-section">
            <h3>
              Source snapshots <Badge>Raw data</Badge>
            </h3>
            {data.snapshots.map((s) => (
              <details className="snapshot-record" key={s.id}>
                <summary>
                  {s.day} · {s.on_hand} on hand · {s.reserved} reserved
                </summary>
                <pre>{JSON.stringify(s, null, 2)}</pre>
              </details>
            ))}
          </div>
          <div className="evidence-section">
            <h3>
              Movement ledger <Badge>Raw data</Badge>
            </h3>
            <p className="text-muted">
              Signed movements after the opening count and through the latest
              reported count.
            </p>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Date / source reference</th>
                    <th>Movement</th>
                    <th className="align-right">Balance change</th>
                  </tr>
                </thead>
                <tbody>
                  {data.movements.map((m) => (
                    <tr key={m.id}>
                      <td>
                        <details>
                          <summary>
                            {m.day}
                            <small>{m.reference}</small>
                          </summary>
                          <pre>{JSON.stringify(m, null, 2)}</pre>
                        </details>
                      </td>
                      <td>{label(m.kind)}</td>
                      <td
                        className={`align-right mono ${m.signed_delta > 0 ? "text-lime" : ""}`}
                      >
                        {m.signed_delta > 0 ? "+" : ""}
                        {m.signed_delta}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <span>
                {offset + 1}–{Math.min(offset + 25, data.total)} of {data.total}{" "}
                movements
              </span>
              <div>
                <button
                  aria-label="Previous movements"
                  disabled={!offset}
                  onClick={() => setOffset(offset - 25)}
                >
                  <ChevronUp size={15} />
                </button>
                <button
                  aria-label="Next movements"
                  disabled={offset + 25 >= data.total}
                  onClick={() => setOffset(offset + 25)}
                >
                  <ChevronDown size={15} />
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="empty">
          <LoaderCircle className="spin" />
        </div>
      )}
    </Modal>
  );
}

function DataPanel({
  batches,
  summary,
  refreshed,
  fail,
}: {
  batches: Batch[];
  summary?: Overview["summary"];
  refreshed: () => void;
  fail: (s: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Batch | null>(null);
  const upload = async () => {
    if (!file) return;
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const report = await api<Batch>("/commands/import", {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: form,
      });
      setResult(report);
      refreshed();
    } catch (e) {
      fail((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="data-layout">
      <section className="panel import-panel">
        <div className="panel-heading">
          <div>
            <h2>Import stock evidence</h2>
            <p>Canonical JSONL or CSV · up to 20 MiB per file</p>
          </div>
          <Upload size={21} />
        </div>
        <div className="upload-area">
          <Database size={33} />
          <h3>Bring your movement ledger into focus</h3>
          <p>
            Import locations and materials first, then movements and daily
            snapshots. Every record needs an ID, source, and ingestion
            timestamp.
          </p>
          <input
            aria-label="Choose inventory file"
            type="file"
            accept=".jsonl,.ndjson,.csv"
            onChange={(e) => {
              setFile(e.target.files?.[0] || null);
              setResult(null);
            }}
          />
          <button className="primary" onClick={upload} disabled={!file || busy}>
            {busy ? (
              <LoaderCircle className="spin" size={16} />
            ) : (
              <Upload size={16} />
            )}
            Validate & import
          </button>
        </div>
        {result && (
          <div
            className={`import-result ${result.status === "rejected" ? "rejected" : ""}`}
            role="status"
          >
            <h3>Batch {result.status}</h3>
            <p>
              {result.accepted} accepted · {result.duplicates} existing records
              · {result.errors.length} errors
            </p>
            {result.status === "accepted" && (
              <p>Run analysis to incorporate new evidence.</p>
            )}
            {result.errors.map((e, i) => (
              <p key={i}>
                Row {e.row}: {e.message}
              </p>
            ))}
          </div>
        )}
      </section>
      <section className="panel data-summary">
        <div className="panel-heading">
          <h2>Dataset at a glance</h2>
        </div>
        {summary ? (
          [
            ["Contractors", summary.contractors],
            ["Materials", summary.skus],
            ["Movement records", summary.movement_count],
            ["Daily counts", summary.snapshot_count],
          ].map(([k, v]) => (
            <div key={k}>
              <span>{k}</span>
              <strong>{number(Number(v))}</strong>
            </div>
          ))
        ) : (
          <p>
            No analysis yet. Import records and run analysis to see measured
            totals.
          </p>
        )}
        <p>
          <ShieldCheck size={18} />
          Imported records retain their source IDs and lineage. Sample files are
          illustrative; workplace results require your own operational evidence.
        </p>
      </section>
      <section className="panel source-guide">
        <div className="panel-heading">
          <div>
            <h2>Where your workplace data comes from</h2>
            <p>
              Exports from your existing systems, mapped to the ConsignAI schema
            </p>
          </div>
          <Database size={21} />
        </div>
        <div className="source-grid">
          <article>
            <span className="eyebrow">01 / CATALOGS</span>
            <h3>ERP & material masters</h3>
            <p>
              SKU, base unit, cost, lead time and pack size. Add enterprise,
              warehouse, contractor and field location IDs.
            </p>
          </article>
          <article>
            <span className="eyebrow">02 / MOVEMENTS</span>
            <h3>WMS & field records</h3>
            <p>
              Receipts, warehouse issues, transfers, actual consumption and
              approved adjustments. Retain source transaction IDs.
            </p>
          </article>
          <article>
            <span className="eyebrow">03 / DAILY COUNTS</span>
            <h3>Contractor & site reports</h3>
            <p>
              End-of-day physical on-hand and reserved units by location and
              SKU. A spreadsheet export can supply this evidence.
            </p>
          </article>
        </div>
        <details className="source-setup">
          <summary>Start with your own data</summary>
          <ol>
            <li>
              Use a separate database and set <code>DEMO_SEED=false</code>{" "}
              before starting it. For Compose, set{" "}
              <code>INVENTORY_DB_FILE=work.db</code> in your local .env.
            </li>
            <li>
              Map source columns to canonical CSV or JSONL. Import locations and
              materials first. Keep units, location IDs, ownership and the
              reporting-day cutoff consistent.
            </li>
            <li>
              Import opening counts, movements and closing counts. Review the
              validation report, then select Run analysis.
            </li>
          </ol>
          <p>
            There are no live ERP connectors or automatic column mappings yet.
            Scheduled exports can use the import API. Movement history without
            independent counts cannot verify physical stock.
          </p>
          <a
            className="secondary template-link"
            href="/templates/workplace-example.jsonl"
            download
          >
            <ArrowDownToLine size={16} />
            Download illustrative import example
          </a>
          <p>
            Example: opening 20 + warehouse issue 10 − usage 4 = expected 26;
            reported 24 gives a variance of −2. Read{" "}
            <code>docs/data-sources.md</code> in the repository for field
            mapping and setup.
          </p>
        </details>
      </section>
      <section className="panel import-history">
        <div className="panel-heading">
          <div>
            <h2>Validation history</h2>
            <p>Accepted and rejected batches remain visible</p>
          </div>
        </div>
        {batches.map((b) => (
          <details className="batch-row" key={b.id}>
            <summary>
              <FileCheck2 size={19} />
              <span>
                <strong>{b.filename}</strong>
                <small>{new Date(b.created_at).toLocaleString()}</small>
              </span>
              <span>{number(b.rows)} rows</span>
              <Badge tone={b.status === "accepted" ? "green" : "red"}>
                {b.status}
              </Badge>
            </summary>
            <div>
              <p>
                {b.accepted} accepted · {b.duplicates} duplicates ·{" "}
                {b.errors.length} errors
              </p>
              {b.errors.map((e, i) => (
                <pre key={i}>
                  Row {e.row}: {e.message}
                </pre>
              ))}
            </div>
          </details>
        ))}
      </section>
    </div>
  );
}

function Architecture({
  overview,
  meta,
  selectedModel,
}: {
  overview: Overview;
  meta: { mode: string; ai_runtime: string; weekly_jobs: boolean } | null;
  selectedModel: string | null;
}) {
  return (
    <div className="architecture">
      <section className="panel architecture-hero">
        <Badge tone="green">OPEN SOURCE / LOCAL FIRST</Badge>
        <h2>
          Numbers from code.
          <br />
          Explanations from evidence.
        </h2>
        <p>
          ConsignAI separates the inventory ledger, analytical models, and
          optional language model. An explanation can fail without changing a
          single balance.
        </p>
        <div className="architecture-flow">
          {[
            ["01", "Evidence", "Validated movements & snapshots"],
            ["02", "Ledger", "Atomic SQLite transactions"],
            ["03", "Analysis", "Accounting, forecasts & constraints"],
            ["04", "Operations", "Exceptions & reviewed proposals"],
          ].map(([n, t, s]) => (
            <div key={n}>
              <span>{n}</span>
              <h3>{t}</h3>
              <p>{s}</p>
            </div>
          ))}
        </div>
      </section>
      <div className="architecture-cards">
        <section className="panel">
          <ShieldCheck />
          <h3>Deterministic foundation</h3>
          <p>
            Opening stock plus signed movements produces the expected balance.
            Robust usage rules and a winsorized consumption forecast expose
            their parameters and evidence.
          </p>
          <code>{overview.algorithm_version}</code>
        </section>
        <section className="panel">
          <Sparkles />
          <h3>Optional local narration</h3>
          <p>
            Ollama receives scoped evidence and returns a validated schema.
            Missing citations, invalid output, and runtime failures fall back to
            an evidence brief. No model has access to mutation tools.
          </p>
          <Badge>{selectedModel || "No model selected"}</Badge>
        </section>
        <section className="panel">
          <Clock3 />
          <h3>Reproducible operations</h3>
          <p>
            Analysis runs are immutable, imports use idempotency keys, and the
            weekly scheduler persists its completed periods. Every API request
            carries a trace ID.
          </p>
          <Badge>
            {meta?.weekly_jobs ? "Weekly jobs enabled" : "Weekly jobs disabled"}
          </Badge>
        </section>
      </div>
      <section className="panel limitations">
        <h3>Know the boundaries</h3>
        <p>
          This is an operational reference implementation using synthetic stock
          data. Consumed quantities may understate true demand during stockouts.
          Redistribution uses transparent greedy rules; it does not claim global
          optimality. Counts use integral base units and a single enterprise
          owner in the demo. Transfers remain proposals. Production deployment
          requires organizational identity, tenant isolation, retention
          policies, backups, and field validation.
        </p>
      </section>
    </div>
  );
}

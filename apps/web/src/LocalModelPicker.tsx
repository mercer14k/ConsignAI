import { useEffect, useState } from "react";
import { Cpu, LoaderCircle, RefreshCw, ShieldCheck } from "lucide-react";
import { api } from "./api";

export interface ModelCatalog {
  runtime: "ollama";
  status: "available" | "empty" | "unavailable";
  models: {
    name: string;
    size_bytes: number;
    digest: string;
    parameter_size: string;
    quantization: string;
  }[];
  excluded_count: number;
  message: string;
}

export function LocalModelPicker({
  selected,
  onSelect,
}: {
  selected: string | null;
  onSelect: (model: string | null) => void;
}) {
  const [catalog, setCatalog] = useState<ModelCatalog | null>(null);
  const [candidate, setCandidate] = useState(selected || "");
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    api<ModelCatalog>("/ai/models", { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) setCatalog(result);
      })
      .catch((e: Error) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [revision]);
  const model = catalog?.models.find((m) => m.name === candidate);
  return (
    <div className="model-picker">
      <div className="model-intro">
        <Cpu size={24} />
        <div>
          <h3>Your device. Your choice.</h3>
          <p>
            Select a text model already installed in your local Ollama runtime.
            No model is selected or downloaded automatically.
          </p>
        </div>
      </div>
      <div className="section-line">
        <span className="eyebrow">INSTALLED MODELS</span>
        <button
          className="secondary"
          onClick={() => setRevision((r) => r + 1)}
          disabled={loading}
        >
          {loading ? (
            <LoaderCircle size={15} className="spin" />
          ) : (
            <RefreshCw size={15} />
          )}
          Refresh models
        </button>
      </div>
      {loading && <p role="status">Checking local Ollama…</p>}
      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}
      {!loading && !error && catalog && <p role="status">{catalog.message}</p>}
      <label className="model-label" htmlFor="local-model">
        AI model
      </label>
      <select
        id="local-model"
        value={model?.name || ""}
        disabled={loading || !!error || !catalog?.models.length}
        onChange={(e) => setCandidate(e.target.value)}
      >
        <option value="">No model selected</option>
        {catalog?.models.map((m) => (
          <option key={m.name} value={m.name}>
            {m.name}
          </option>
        ))}
      </select>
      {model && !loading && !error && (
        <dl className="model-details">
          <div>
            <dt>Local weights</dt>
            <dd>{(model.size_bytes / 1024 ** 3).toFixed(2)} GiB</dd>
          </div>
          <div>
            <dt>Parameters</dt>
            <dd>{model.parameter_size || "Not reported"}</dd>
          </div>
          <div>
            <dt>Quantization</dt>
            <dd>{model.quantization || "Not reported"}</dd>
          </div>
        </dl>
      )}
      {!!catalog?.excluded_count && (
        <p className="text-muted">
          {catalog.excluded_count} remote, unsupported, or unverifiable model
          entries excluded.
        </p>
      )}
      <p className="model-note">
        <ShieldCheck size={17} />
        This choice lasts for this page session. Refreshing the page clears it.
        Inventory calculations always work without AI.
      </p>
      <p className="text-muted">
        Models belong to the machine running the API. For a local installation,
        that is your device. Review the license of your selected weights.
      </p>
      <div className="model-actions">
        <button className="secondary" onClick={() => onSelect(null)}>
          Use without AI
        </button>
        <button
          className="primary"
          disabled={!model || loading || !!error}
          onClick={() => model && onSelect(model.name)}
        >
          Use selected model
        </button>
      </div>
    </div>
  );
}

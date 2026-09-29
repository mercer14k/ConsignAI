"""Discover installed models without downloading, loading, or selecting one."""

from urllib.parse import urlparse

import httpx
from pydantic import ValidationError

from consignai.domain.schemas import LocalModel, ModelCatalog


def local_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if (
        parsed.hostname not in {"127.0.0.1", "localhost", "ollama", "host.docker.internal", "::1"}
        or parsed.scheme != "http"
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Only explicitly allowed local model hosts may be used")
    return base_url.rstrip("/")


def installed_models(client: httpx.Client, base_url: str) -> tuple[list[LocalModel], int]:
    response = client.get(f"{local_url(base_url)}/api/tags", timeout=3)
    response.raise_for_status()
    rows = response.json()["models"]
    if not isinstance(rows, list):
        raise ValueError("Invalid model catalog")
    found, excluded = {}, 0
    for row in rows:
        try:
            name = row["name"]
            if row.get("remote_model") or row.get("remote_host") or "cloud" in name.casefold():
                excluded += 1
                continue
            details = row.get("details") or {}
            capabilities = row.get("capabilities")
            if details.get("format") != "gguf" or (capabilities and "completion" not in capabilities):
                excluded += 1
                continue
            model = LocalModel(
                name=name,
                size_bytes=row["size"],
                digest=row["digest"],
                parameter_size=details.get("parameter_size", ""),
                quantization=details.get("quantization_level", ""),
            )
            found[model.name] = model
        except (ValidationError, KeyError, TypeError, AttributeError):
            excluded += 1
    return sorted(found.values(), key=lambda m: m.name), excluded


def discover_models(base_url: str) -> ModelCatalog:
    try:
        with httpx.Client(trust_env=False) as client:
            models, excluded = installed_models(client, base_url)
        return ModelCatalog(
            status="available" if models else "empty",
            models=models,
            excluded_count=excluded,
            message="Choose a model explicitly. Nothing is selected automatically."
            if models
            else "No eligible local text models found. Install a model in Ollama, then refresh.",
        )
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
        return ModelCatalog(
            status="unavailable",
            models=[],
            excluded_count=0,
            message="Cannot read local models. Start Ollama and check OLLAMA_BASE_URL on the API host. Computed briefs still work.",
        )


def verify_model(client: httpx.Client, base_url: str, model: str) -> LocalModel:
    models, _ = installed_models(client, base_url)
    selected = next((m for m in models if m.name == model), None)
    if selected is None:
        raise ValueError(
            "Selected model is not installed as an eligible local model. Refresh the model list."
        )
    # Inspect again just before sending evidence; aliases may have changed since discovery.
    response = client.post(f"{base_url}/api/show", json={"model": model}, timeout=5)
    response.raise_for_status()
    details = response.json()
    if (
        details.get("remote_model")
        or details.get("remote_host")
        or details.get("details", {}).get("format") != "gguf"
        or "completion" not in details.get("capabilities", [])
    ):
        raise ValueError("Selected model must have local weights and text completion capability")
    return selected

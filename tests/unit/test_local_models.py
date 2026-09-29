import json

import httpx
import pytest
from consignai.ai.catalog import discover_models, local_url
from consignai.ai.explain import OllamaRuntime, explain


def model_entry(name="chosen-model:small", **extra):
    return {
        "name": name,
        "size": 1000000,
        "digest": "sha256:fixture",
        "details": {"format": "gguf", "parameter_size": "1B", "quantization_level": "Q4_K_M"},
        **extra,
    }


@pytest.fixture
def mock_local(monkeypatch):
    original = httpx.Client

    def install(handler):
        monkeypatch.setattr(
            httpx, "Client", lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handler))
        )

    return install


def test_runtime_requires_explicit_model():
    with pytest.raises(TypeError):
        OllamaRuntime()
    with pytest.raises(ValueError):
        OllamaRuntime("")


def test_catalog_never_selects_and_excludes_remote_aliases(mock_local):
    mock_local(
        lambda r: httpx.Response(
            200,
            json={
                "models": [
                    model_entry(),
                    model_entry("cloud-model:cloud"),
                    model_entry("innocent-alias", remote_host="https://ollama.com"),
                    model_entry("another-alias", remote_model="upstream"),
                    model_entry("embedder", capabilities=["embedding"]),
                    model_entry("not-local", size=0),
                    {"bad": "entry"},
                ]
            },
        )
    )
    result = discover_models("http://localhost:11434")
    assert result.status == "available"
    assert [m.name for m in result.models] == ["chosen-model:small"]
    assert result.excluded_count == 6
    assert "selected_model" not in result.model_dump()


@pytest.mark.parametrize("body", [{"models": []}, {"models": [model_entry(remote_model="cloud")]}])
def test_empty_catalog_is_visible(mock_local, body):
    mock_local(lambda r: httpx.Response(200, json=body))
    assert discover_models("http://localhost:11434").status == "empty"


def test_offline_and_malformed_catalogs_are_visible(mock_local):
    def offline(request):
        raise httpx.ConnectError("offline", request=request)

    mock_local(offline)
    assert discover_models("http://localhost:11434").status == "unavailable"
    mock_local(lambda r: httpx.Response(200, json={"models": None}))
    assert discover_models("http://localhost:11434").status == "unavailable"


@pytest.mark.parametrize(
    "url",
    [
        "https://ollama.com",
        "http://evil.test",
        "http://localhost/x",
        "http://user:pass@localhost",
        "http://localhost?proxy=cloud",
    ],
)
def test_remote_or_ambiguous_endpoints_rejected(url):
    with pytest.raises(ValueError):
        local_url(url)


@pytest.mark.parametrize(
    "model_name,show,expected_paths",
    [
        ("not-installed", {}, ["/api/tags"]),
        ("chosen-model:small", {"remote_model": "upstream"}, ["/api/tags", "/api/show"]),
        ("chosen-model:small", {"capabilities": ["embedding"]}, ["/api/tags", "/api/show"]),
    ],
)
def test_selected_model_cannot_route_to_remote_or_replacement(mock_local, model_name, show, expected_paths):
    paths = []

    def handler(request):
        paths.append(request.url.path)
        return httpx.Response(
            200, json={"models": [model_entry()]} if request.url.path == "/api/tags" else show
        )

    mock_local(handler)
    alert = {
        "kind": "variance",
        "title": "Variance",
        "severity": "high",
        "detail": "Computed 2 units",
        "evidence_ids": ["record-1"],
    }
    result = explain(
        alert, [{"id": "record-1", "source_id": "work", "record_type": "snapshot"}], OllamaRuntime(model_name)
    )
    assert result["mode"] == "deterministic_fallback"
    assert result["explanation"]["summary"] == alert["detail"]
    assert paths == expected_paths  # No evidence-bearing chat request was sent.


def test_exact_selected_model_is_used_and_digest_recorded(mock_local):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [model_entry("first-model:small"), model_entry()]})
        if request.url.path == "/api/show":
            assert json.loads(request.content)["model"] == "chosen-model:small"
            return httpx.Response(200, json={"details": {"format": "gguf"}, "capabilities": ["completion"]})
        payload = json.loads(request.content)
        assert payload["model"] == "chosen-model:small"
        answer = {
            "status": "explained",
            "summary": payload["format"]["properties"]["summary"]["enum"][0],
            "evidence_ids": ["record-1"],
            "next_action": "verify_count",
        }
        return httpx.Response(
            200,
            json={"model": payload["model"], "message": {"content": json.dumps(answer)}, "eval_count": 20},
        )

    mock_local(handler)
    alert = {
        "kind": "variance",
        "title": "Variance",
        "severity": "high",
        "detail": "Computed 2 units",
        "evidence_ids": ["record-1"],
    }
    result = explain(
        alert,
        [{"id": "record-1", "source_id": "work", "record_type": "snapshot"}],
        OllamaRuntime("chosen-model:small"),
    )
    assert result["mode"] == "local_ai"
    assert result["telemetry"]["model"] == "chosen-model:small"
    assert result["telemetry"]["model_digest"] == "sha256:fixture"
    assert calls == ["/api/tags", "/api/show", "/api/chat"]

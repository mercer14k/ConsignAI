# Open-source and model licenses

ConsignAI source code and original documentation: **Apache License 2.0**, see [LICENSE](../LICENSE). Synthetic data and original screenshots are provided under the same project license. No proprietary fonts, telemetry assets, cloud AI clients, paid service dependencies or model weights are required or bundled.

## Material dependencies

| Component | License | Role / source |
|---|---|---|
| Python | PSF License | Language runtime; [python.org](https://www.python.org/psf/license/) |
| FastAPI | MIT | REST API; [repository](https://github.com/fastapi/fastapi) |
| Pydantic / pydantic-core | MIT | Typed records and structured model outputs; [repository](https://github.com/pydantic/pydantic) |
| Starlette / AnyIO | BSD-3-Clause / MIT | ASGI and concurrency; [Starlette](https://github.com/Kludex/starlette), [AnyIO](https://github.com/agronholm/anyio) |
| Uvicorn | BSD-3-Clause | ASGI server; [repository](https://github.com/Kludex/uvicorn) |
| HTTPX / httpcore | BSD-3-Clause | Local model HTTP transport; [repository](https://github.com/encode/httpx) |
| NumPy | BSD-3-Clause, bundled notices for native libraries | Explicit statistical calculations; [license](https://numpy.org/doc/stable/license.html) |
| SQLite | Public domain | Embedded database; [copyright statement](https://sqlite.org/copyright.html) |
| python-multipart | Apache-2.0 | Upload parsing; [repository](https://github.com/Kludex/python-multipart) |
| React / React DOM | MIT | UI; [repository](https://github.com/facebook/react) |
| TypeScript | Apache-2.0 | Static frontend contracts; [repository](https://github.com/microsoft/TypeScript) |
| Vite / Vitest | MIT | Build and component testing; [Vite](https://github.com/vitejs/vite), [Vitest](https://github.com/vitest-dev/vitest) |
| Apache ECharts / zrender | Apache-2.0 / BSD-3-Clause | Charts and rendering; [ECharts](https://github.com/apache/echarts), [zrender](https://github.com/ecomfe/zrender) |
| Lucide | ISC | Interface icons; [license](https://lucide.dev/license) |
| Node.js / pnpm | MIT (Node includes third-party notices) | Frontend tooling; [Node](https://github.com/nodejs/node), [pnpm](https://github.com/pnpm/pnpm) |
| Nginx | BSD-2-Clause | Static serving/proxy; [license](https://nginx.org/LICENSE) |
| Docker Engine / Compose | Apache-2.0 | Local container orchestration; [Moby](https://github.com/moby/moby), [Compose](https://github.com/docker/compose) |
| Ollama | MIT | Optional local model runtime; [license](https://github.com/ollama/ollama/blob/main/LICENSE) |
| pytest / pytest-cov / coverage.py | MIT / MIT / Apache-2.0 | Backend verification |
| Ruff / ESLint / Prettier | MIT / MIT / MIT | Lint and formatting |
| Playwright | Apache-2.0 | Browser tests; browser distributions have their own notices |
| Testing Library | MIT | UI tests |
| axe-core / @axe-core/playwright | MPL-2.0 / MPL-2.0 | Accessibility checks, development-only; [repository](https://github.com/dequelabs/axe-core) |
| pip-audit | Apache-2.0 | Dependency advisory checks |
| jsonschema | MIT | Canonical schema validation in development |
| GitHub official checkout/setup/upload actions | MIT | CI tooling; GitHub-hosted execution is optional to local tests |

Pinned Python versions are in `requirements.lock`; frontend versions are in `apps/web/pnpm-lock.yaml`. Machine-readable dependency inventories accompany this file in `docs/benchmarks`. Transitive wheels, distributions, base images and browser binaries can include additional notices; preserve their license files when redistributing them. The inventory is metadata evidence, not legal advice or a complete container SBOM.

## Optional model weights

- **Qwen2.5 1.5B:** Apache-2.0, [exact Ollama model license](https://ollama.com/library/qwen2.5:1.5b/blobs/832dd9e00a68). Explicitly tested weight variant; not a default, not selected automatically, and not bundled.
- **Qwen3 8B:** Apache-2.0, [model card](https://huggingface.co/Qwen/Qwen3-8B). Used for the build machine's optional local smoke test because it was already installed.

Licenses differ across models and even sizes within one family. Do not assume that all Qwen, Llama or other open-weight variants share a license. Check the exact artifact and retain attribution before distributing weights. Open-weight does not automatically mean OSI-approved open-source training data or unrestricted use.

Docker Desktop is an optional convenience with separate commercial terms; it is not a project dependency or the only supported way to run Compose. The core path requires open-source Docker Engine/Compose or a compatible local container runtime. Nothing requires a paid hosted AI API.

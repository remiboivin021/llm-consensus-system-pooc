## LCS — LLM Consensus Service

Python-only FastAPI service, CLI, and observability stack for majority-vote LLM consensus with deterministic similarity scoring.

### Features
- Majority-vote consensus via cheap deterministic embeddings + cosine similarity.
- FastAPI endpoints: `/v1/consensus`, `/health`, `/ready`, `/metrics`.
- Typer CLI (local core call or remote via `API_URL`).
- Prometheus metrics, OpenTelemetry traces/logs (Tempo/Loki), Grafana dashboards.
- Mock-friendly provider layer (OpenRouter-compatible) with offline test suite.

### Setup
1) Install dependencies:
```bash
poetry install
```
2) Configure environment (copy and edit `.env.example`):
```bash
cp .env.example .env
```

### Run the API
```bash
poetry run uvicorn sample.api.app:app --host 0.0.0.0 --port 8000
```

### CLI
Local core (no API required):
```bash
poetry run lcs consensus --prompt "Hello" --models "model-a,model-b"
```
Remote API call (set `API_URL`, e.g. `http://localhost:8000`):
```bash
API_URL=http://localhost:8000 poetry run lcs consensus --prompt "Hello"
```

LLM Consensus System (LCS) is a service that computes a single consensus response from multiple LLM outputs. Clients send a consensus request to a REST/JSON API.
The API validates input and forwards it to the consensus core, which triggers LLM adapters to produce candidate responses, computes consensus and scoring, emits metrics, logs runs (optional in MVP, required in V1+), and returns the final response.
The architecture emphasizes scalability, modularity, and fault tolerance through a consensus engine, API gateway, state management, and monitoring/logging components, with Rust used for orchestration and security-sensitive logic and Python used for LLM execution.
### Tests
```bash
poetry run pytest -q
```

### Lint/Format
```bash
poetry run ruff check .
poetry run black --check .
```

### Docker Compose (app + observability)
```bash
docker compose up --build
```
Prometheus: `localhost:9090` — Grafana: `localhost:3000` (datasources auto-provisioned).



### Built With

* [![Rust][Rust]][Rust-url]
* [![Python][Python]][Python-url]
* [![Docker][Docker.io]][Docker-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>


## Getting Started

This repository includes local setup guidance and operational details in `docs/`. Start with the folders in the Documentation section below and follow the relevant instructions for your role or task.

### Documentation

You can find all the documentation you may need in ``docs/``

| Documentation | Location | Purpose |
|---------------|----------|---------|
| API | `docs/api/` | Endpoints, auth, errors, and versioning details. |
| Architecture | `docs/architecture/` | System structure, boundaries, and C4 diagrams. |
| Change Management | `docs/change_management/` | Change control, release management, and templates. |
| Deployment | `docs/deployment/` | Runtime assumptions and deployment guidance. |
| Design | `docs/design/` | Design principles, patterns, and component roles. |
| Engineering | `docs/engineering/` | Engineering principles, standards, and guidelines. |
| Governance | `docs/governance/` | Contribution model and decision processes. |
| Maintenance | `docs/maintenance/` | Health checks, troubleshooting, and upkeep practices. |
| References | `docs/references/` | Glossary, abbreviations, and supporting references. |
| Security | `docs/security/` | Security goals, policies, and controls. |
| Testing | `docs/testing/` | Test strategy, plans, and reports. |
| Tooling | `docs/tooling/` | Toolchain, CI, and documentation rules. |
| Rust Modules | `rust/docs/` | Rust module boundaries and conventions. |
| Python Modules | `python/docs/` | Python module boundaries and conventions. |

### Prerequisites

- [Docker](https://docs.docker.com/desktop/setup/install/linux/)

### Installation

TBD

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

TBD

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Roadmap

Summary only. Full details are in `docs/governance/roadmap.md`.

### MVP
- [ ] REST/JSON consensus endpoint
- [ ] Basic logging in SQLite + privacy rules
- [ ] Minimal benchmark harness + stability signal

### V1
- [ ] Versioned API + run retrieval
- [ ] Judge-based scoring + regression gating
- [ ] Metrics endpoint + retention policy

### V2
- [ ] Evidence mode endpoint
- [ ] Dataset benchmarks + drift metrics
- [ ] Local NoSQL long-term logging

See the full roadmap in `docs/governance/roadmap.md`.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Security

Please report security issues privately. See [`SECURITY.md`](./SECURITY.md).

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

For more info please read the [CONTRIBUTING.md file](./CONTRIBUTING.md) and the [GIT.md file](./GIT.md) to know how we use git/github

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Top contributors:

<a href="https://github.com/remiboivin021/llm-consensus-system/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=remiboivin021/llm-consensus-system" alt="contrib.rocks image" />
</a>

## License

Distributed under the MIT license. See [`LICENSE`](./LICENSE) for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contact

remiboivin021[at]gmail[dot]com

Project Link: [https://github.com/remiboivin021/llm-consensus-system](https://github.com/remiboivin021/llm-consensus-system)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

[contributors-shield]: https://img.shields.io/github/contributors/remiboivin021/llm-consensus-system.svg?style=for-the-badge
[contributors-url]: https://github.com/remiboivin021/llm-consensus-system/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/remiboivin021/llm-consensus-system.svg?style=for-the-badge
[forks-url]: https://github.com/remiboivin021/llm-consensus-system/network/members
[stars-shield]: https://img.shields.io/github/stars/remiboivin021/llm-consensus-system.svg?style=for-the-badge
[stars-url]: https://github.com/remiboivin021/llm-consensus-system/stargazers
[issues-shield]: https://img.shields.io/github/issues/remiboivin021/llm-consensus-system.svg?style=for-the-badge
[issues-url]: https://github.com/remiboivin021/llm-consensus-system/issues
[license-shield]: https://img.shields.io/github/license/remiboivin021/llm-consensus-system.svg?style=for-the-badge
[license-url]: https://github.com/remiboivin021/llm-consensus-system/blob/main/LICENSE

[product-screenshot]: images/screenshot.png
<!-- TODO: Rewrite this to use the rights shields icons. Just facts. You'll be rewarded if you don't assume things -->

[Rust]: https://img.shields.io/badge/Rust-000000?style=for-the-badge&logo=rust&logoColor=white
[Rust-url]: https://www.rust-lang.org/
[Python]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[Docker.io]: https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white
[Docker-url]: https://www.docker.com/
### Dev Compose with Hot Reload
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```
This overrides the app service to use `Dockerfile.dev`, mounts the repo, and runs `uvicorn --reload` for live code changes.

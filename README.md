## LCS — LLM Consensus Library

Python-only library for consensus across multiple LLM candidates with deterministic similarity scoring and optional quality scoring. No bundled HTTP API or CLI; embed `src` in your own app and wire endpoints/metrics as you wish.

> Package name on PyPI: `lcs`; import path: `src.*` (the published wheel installs a `src` package).

### Features (library)
- Majority-vote and score-preferred judges (similarity + optional code quality scoring).
- Policy guardrails (model allowlist, min/max models, pre/post gating, provider failure/timeout ratios).
- Timeouts overridable via policy (e2e + provider).
- Mock-friendly provider adapter (OpenRouter-compatible) with offline test suite.
- Observability helpers (logging/tracing/metrics) — opt-in, call `configure_logging/tracing` from your host app.

### Setup
1) Install dependencies:
```bash
poetry install
```
2) Configure environment (copy and edit `.env.example`):
```bash
cp .env.example .env
```

### Usage
Import the library in your own app or script (module path is `src.*`; install as `lcs`):
```python
import asyncio
from src import LcsClient
from src.contracts.request import ConsensusRequest

async def main():
    client = LcsClient()
    req = ConsensusRequest(prompt="Hello world", models=["model-a", "model-b"])
    result = await client.run(req, strategy="majority_cosine")
    print(result.winner, result.confidence)

asyncio.run(main())
```

LLM Consensus System (LCS) is a library that computes a single consensus response from multiple LLM outputs. Build your own API/CLI around it if needed.
### Tests
```bash
poetry run pytest -q
```

### Lint/Format
```bash
poetry run ruff check .
poetry run black --check .
```

### Built With
* [![Python][Python]][Python-url]

## Getting Started

This repository includes local setup guidance and operational details in `docs/`. Start with the folders in the Documentation section below and follow the relevant instructions for your role or task.

### Documentation

You can find all the documentation you may need in ``docs/``

| Documentation | Location | Purpose |
|---------------|----------|---------|
| Architecture | `docs/architecture/` | System structure, boundaries, and C4 diagrams. |
| Governance | `docs/governance/` | Contribution model and decision processes. |
| Security | `docs/security/` | Security goals, policies, and controls. |
| Testing | `docs/testing/` | Test strategy, plans, and reports. |
| Engineering | `docs/engineering/` | Engineering principles, standards, and guidelines. |
| Tooling | `docs/tooling/` | Toolchain, CI, and documentation rules. |
| Change Management | `docs/change_management/` | Change control, release management, and templates. |
| References | `docs/references/` | Glossary, abbreviations, and supporting references. |

### Prerequisites
- Python 3.11+
- Poetry

## Roadmap

Library roadmap (see `docs/governance/roadmap.md` for details):
- Expand judge options (LLM-judge, reliability-weighted voting).
- Harden scoring signals and regression gates.
- Optional reference API/CLI examples (out-of-tree).

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

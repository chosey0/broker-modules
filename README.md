# Broker Modules

Pure Python broker SDK collection used by FinLabs and other internal projects.

## Install with uv

```toml
[project]
dependencies = ["finlabs-brokers"]

[tool.uv.sources]
finlabs-brokers = { git = "https://github.com/chosey0/broker-modules.git" }
```

For local development next to the FinLabs repository:

```toml
[tool.uv.sources]
finlabs-brokers = { path = "../broker-modules", editable = true }
```

## Import

```python
from brokers.kiwoom import KiwoomClient
from brokers.kis import KisClient
from brokers.krx import KrxClient
from brokers.toss import TossClient
```

## Development

```bash
uv sync
uv run python -m pytest tests/brokers -q
uv run ruff check brokers tests
uv build --wheel
```

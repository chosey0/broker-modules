<div align="center">

# Broker Modules

**KIS, Kiwoom, Toss, KRX Open API를 재사용 가능한 Python SDK로 제공하는 브로커 모듈 패키지**

[![Python](https://img.shields.io/badge/Python_3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![HTTPX](https://img.shields.io/badge/HTTPX-0.27+-2F6F9F?style=for-the-badge)](https://www.python-httpx.org/)
[![WebSockets](https://img.shields.io/badge/WebSockets-13+-010101?style=for-the-badge)](https://websockets.readthedocs.io/)
[![pytest](https://img.shields.io/badge/Tested_with-pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://pytest.org/)

증권사 Open API 인증, REST 조회, WebSocket 실시간 시세, 응답 파싱을 **FinLabs와 분리된 순수 SDK**로 제공합니다.

[FinLabs](https://github.com/chosey0/finlabs) · [KIS SDK](./brokers/kis/README.md) · [Kiwoom SDK](./brokers/kiwoom/README.md) · [Toss SDK](./brokers/toss/README.md) · [KRX SDK](./brokers/krx/README.md)

</div>

---

## Overview

`broker-modules`는 여러 프로젝트에서 공통으로 사용할 수 있는 브로커 SDK 모음입니다.
패키지명은 `broker-modules`이고, Python import namespace는 `brokers.*`입니다.

이 리포지토리는 브로커별 전송, 인증, 엔드포인트 정의, 응답 파싱, broker-native 모델만
소유합니다. FinLabs의 adapter, orchestration, storage, CLI, dashboard, research 코드는
이 리포지토리에 포함하지 않습니다.

---

## Components

| | 영역 | 상태 | 설명 |
|---|------|:----:|------|
| **[KIS]** | [KIS SDK](./brokers/kis/README.md) | 구현 중 | 한국투자증권 국내·해외 REST 조회, 해외·국내 WebSocket 실시간 시세, 인증, 심볼 마스터 |
| **[Kiwoom]** | [Kiwoom SDK](./brokers/kiwoom/README.md) | 구현 중 | 키움증권 OAuth, 국내주식 차트, 업종 코드·지수, 국내 실시간 체결·호가·업종지수와 미국주식 체결가·10호가 WebSocket |
| **[Toss]** | [Toss SDK](./brokers/toss/README.md) | 구현됨 | 토스증권 현재가·캔들·종목정보와 국내·해외 장 운영 정보 조회 |
| **[KRX]** | [KRX SDK](./brokers/krx/README.md) | 초기 구현 | KRX Data Marketplace 지수 일별 가격 조회 |

---

## Features

| | 기능 | 설명 |
|---|------|------|
| **[인증]** | 브로커별 토큰 발급·캐시 | KIS, Kiwoom, Toss 인증 흐름과 메모리 토큰 캐시 |
| **[REST]** | 시세·차트 조회 | 브로커별 엔드포인트 정의와 typed client facade |
| **[Realtime]** | WebSocket 세션 | KIS 및 Kiwoom 국내·미국주식 실시간 체결·호가 구독과 프레임 파싱 |
| **[Models]** | broker-native dataclass | SDK 응답을 저장소나 canonical 모델에 묶지 않는 순수 모델 |
| **[Parsers]** | 응답 정규화 | 문자열 숫자, 날짜, 시간, continuation 응답 파싱 |
| **[Isolation]** | FinLabs 비의존 | DuckDB, CLI, adapters, orchestration, domain 계층을 import하지 않음 |

### Realtime Ordering Contract

WebSocket 실시간 이벤트는 `received_at`과 `received_seq`를 함께 제공합니다.
`received_at`은 SDK가 프레임을 파싱한 수신 시각이고, `received_seq`는 단일
WebSocket 세션 안에서 SDK가 부여하는 단조 증가 순번입니다. 같은
`received_at`을 가진 이벤트를 저장하거나 재생할 때는
`(received_at, received_seq)`로 정렬해야 로컬 수신 순서가 보존됩니다.

이 순번은 로컬 수신 순서용 tie-breaker입니다. 여러 WebSocket 연결, 재접속
전후, 별도 프로세스 수집 간 전역 순서나 거래소의 절대 발생 순서를 보장하지는
않습니다.

---

## Tech Stack

### Runtime

![Python](https://img.shields.io/badge/Python_3.12+-3776AB?style=flat-square&logo=python&logoColor=white)
![HTTPX](https://img.shields.io/badge/HTTPX-0.27+-2F6F9F?style=flat-square)
![WebSockets](https://img.shields.io/badge/WebSockets-13+-010101?style=flat-square)

### Quality

![pytest](https://img.shields.io/badge/pytest-9.0+-0A9EDC?style=flat-square&logo=pytest&logoColor=white)
![Ruff](https://img.shields.io/badge/Ruff-0.15+-D7FF64?style=flat-square&logo=ruff&logoColor=black)
![uv](https://img.shields.io/badge/uv-package_manager-5C4EE5?style=flat-square)

---

## Architecture

`broker-modules`는 SDK 경계만 담당합니다. 상위 프로젝트는 이 SDK를 직접 사용하거나,
별도의 adapter 계층에서 canonical model로 변환합니다.

```text
consumer app / FinLabs CLI / service
        │
        ▼
brokers.{broker}.Client              transport and auth
        │
        ├──────────────▶ brokers.{broker}.endpoints
        ├──────────────▶ brokers.{broker}.parsers
        ▼
brokers.{broker}.models              broker-native dataclasses
```

| 계층 | 위치 | 책임 |
|------|------|------|
| Package root | `brokers/` | 브로커 SDK namespace |
| Broker SDK | `brokers/{kis,kiwoom,toss,krx}/` | 인증, API 요청, 응답 파싱, native 모델 |
| Internal helpers | `brokers/{broker}/_internal/` | 헤더, HTTP transport, pacing 등 SDK 내부 유틸 |
| Tests | `tests/brokers/` | 네트워크 없는 단위 테스트와 parser/client contract 검증 |

금지되는 의존성:

```text
brokers.* -> FinLabs modules.adapters
brokers.* -> FinLabs modules.orchestration
brokers.* -> FinLabs modules.storage
brokers.* -> FinLabs modules.domain
brokers.* -> finlabs_cli / dashboard / research
```

---

## Repository

```text
broker-modules/
├── brokers/
│   ├── kis/          한국투자증권 국내·해외주식 REST/WebSocket SDK
│   ├── kiwoom/       키움증권 국내 차트·업종 및 국내·미국 실시간 SDK
│   ├── toss/         토스증권 국내·미국주식 시세·장운영 SDK
│   └── krx/          KRX 지수 데이터 SDK
├── tests/
│   └── brokers/      브로커 SDK 단위 테스트
├── pyproject.toml    패키지 메타데이터
├── uv.lock           개발 환경 lockfile
└── README.md         프로젝트 개요
```

---

## Getting Started

### Install With uv

```toml
[project]
dependencies = ["broker-modules"]

[tool.uv.sources]
broker-modules = { git = "https://github.com/chosey0/broker-modules.git" }
```

설치:

```bash
uv sync
```

로컬에서 FinLabs와 나란히 개발할 때:

```toml
[tool.uv.sources]
broker-modules = { path = "../broker-modules", editable = true }
```

### Import

```python
from brokers.kis import KisClient
from brokers.kiwoom import KiwoomClient
from brokers.krx import KrxClient
from brokers.toss import TossClient
```

### Development

```bash
uv sync
uv run python -m pytest tests/brokers -q
uv run ruff check brokers tests
uv build --wheel
```

---

## Notes

- 실거래, 주문 실행, 전략, 백테스트는 이 SDK의 범위가 아닙니다.
- 로컬 `.env`, broker credential, token cache, DB 파일은 커밋하지 않습니다.
- 네트워크가 필요한 실제 API smoke test는 각 브로커 계정과 환경변수 설정 후 별도로 수행합니다.

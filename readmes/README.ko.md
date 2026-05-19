# AutoPaperToPPT

[![CI](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![Python](https://img.shields.io/pypi/pyversions/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/AutoPaperToPPT.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/autopapertoppt/badge/?version=latest)](https://autopapertoppt.readthedocs.io/en/latest/)

> **언어**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · **한국어** · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **문서**: [autopapertoppt.readthedocs.io](https://autopapertoppt.readthedocs.io/en/latest/)

키워드 기반 논문 검색 어시스턴트. arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (Crossref 경유), IEEE Xplore, DBLP, 일반 Crossref, OpenAIRE, Springer Nature, Google Scholar 에서 결과를 가져와 단일 레코드 형식으로 정규화하고, 중복 제거된 결과를 **논문 발표용 PowerPoint 슬라이드**, **Excel 워크북**, **BibTeX 파일** 로 내보냅니다 — CLI 호출 한 번 또는 MCP 도구 호출 한 번으로 끝납니다. 각 논문의 PDF 를 읽고 구조화된 요약을 생성할 수도 있으며 (LLM-as-agent 경로), 또는 Anthropic API 경유 (Python 파이프라인 경로) 가능합니다.

## 본 프로젝트를 구동하는 AI 에이전트에게

**당신이 LLM (Claude Code, Cursor, Aider, Codex CLI, …) 으로 무엇을 해야 할지 파악하기 위해 이 README 를 읽고 있다면 — 여기서 시작하세요.** 같은 규칙이 [`AGENTS.md`](AGENTS.md) (에이전트 간 미러) 와 [`CLAUDE.md`](CLAUDE.md) (정식 참조) 에도 고정되어 있습니다. 사소하지 않은 변경 전에 반드시 그쪽을 먼저 읽으세요.

### 사용자가 실제로 원하는 것

기본 산출물은 **논문 한 편당 논문 발표급 리치 `.pptx`** 입니다. CLI 가 기본으로 내놓는 초록만 있는 라이트 덱이 아닙니다. 라이트 출력은 중간 산출물 — 그것을 업그레이드하는 것이 당신의 일입니다.

### 의사결정 트리

1. 환경에 `ANTHROPIC_API_KEY` 가 설정되어 있는가? → CLI 만 실행하세요. Anthropic API 경유로 자동 enrich 됩니다. 끝.
2. 키 없음, 하지만 당신 (LLM) 이 세션을 구동 → **리치 요약을 직접 작성**. 각 PDF 를 읽고, rich-tier 필드 (`pain_points`, `research_question`, `contributions_detailed`, `headline_metrics`, `technique_table`, `method_sections`, `evaluation_sections`, `system_flow`, `research_questions`, `rq_results`, `core_observation`, `limitations`, `future_work`) 로 `PaperSummary` 를 손으로 작성, `scripts/regen_<query>.py` 를 두고 실행하세요. **사용자에게 API 키를 설정하라고 하지 마세요** — 당신이 요약을 작성했어야 할 LLM 입니다.
3. 루프에 LLM 없음 (CI / cron / 무인) → 라이트 출력 허용.

### MCP 6 단계 워크플로

```
1. (선택) list_sources()                                  # 활성화된 플러그인 확인
2. search(keywords, sources, top_tier_only=true, ...)
3. (선택) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # 논문별
5. (각 PDF 를 읽고 구조화된 summary dict 생성)
6. export(papers=[{...paper, "summary": {...}}], language="ko", ...)
```

11 개의 MCP 도구 (`list_sources`, `download_pdfs`, `pptx_inspect` / `pptx_update_slide` / `pptx_add_slide` 등) 의 전체 참조는 [`docs/mcp.md`](docs/mcp.md) 에 있습니다.

### 필수: 인도 전 URL / DOI 검증

출판사 URL 경로는 **추측할 수 없습니다** — AAAI 는 숫자 ID (`v40i5.37389`), IEEE 는 불투명한 `arnumber`, ACM 은 불투명한 DOI 를 사용합니다. `Paper` 를 손으로 작성할 때 `url` / `doi` / `arxiv_id` 는 **이 검색이 생성한 xlsx 에서 글자 그대로 복사** 하세요 — 기억에서 쓰거나 제목으로부터 구성하지 마세요.

xlsx 는 `exports/<run>/<slug>-<timestamp>.xlsx` 에 작성되며, 열 7 = DOI, 열 8 = URL 입니다. regen 스크립트 종료 후 다음 감사를 실행하세요:

```python
from openpyxl import load_workbook
from scripts.regen_<run> import ALL_PAPERS
real = {sh.cell(row=r, column=2).value: sh.cell(row=r, column=8).value
        for sh in [load_workbook("exports/<run>/<slug>-<ts>.xlsx")["Papers"]]
        for r in range(2, sh.max_row + 1)}
for p in ALL_PAPERS:
    actual = next((u for t, u in real.items() if p.title[:30] in (t or "")), None)
    if actual and not (p.url == actual
                       or p.url.split("v")[0] == actual.split("v")[0]):
        print(f"! {p.bibtex_key()} authored {p.url} vs real {actual}")
```

프로덕션에서 이렇게 잡힌 두 건의 조작: 잘못된 AAAI 권호 (`v39i23.34521` vs 실제 `v39i22.34537`), 그리고 발명한 저자 slug 경로 (`view/fang2026` 대신 `v40i5.37389`).

### 작업 예제

[`scripts/regen_llm_security_batch.py`](scripts/regen_llm_security_batch.py) 에 이 절차대로 손으로 작성한 8 편의 리치 요약이 포함되어 있습니다. 다중 논문 검색의 템플릿으로 사용하세요. zh-tw 짝은 [`scripts/regen_llm_security_batch_zh_tw.py`](scripts/regen_llm_security_batch_zh_tw.py).

### 금지

- **하지 말 것**: 다중 논문 검색 종료 시 사용자에게 "리치 덱을 위해 `ANTHROPIC_API_KEY` 를 설정하세요" 라고 말하기 — 요약을 작성할 수 있었을 LLM 이 바로 당신.
- **하지 말 것**: 논문별 라이트 `.pptx` 를 산출물로 취급하기.
- **하지 말 것**: `download_pdfs` 가 "N 개 PDF 저장됨" 을 보고할 때 멈추기 — 리치 작성 단계의 시작이지 끝이 아닙니다.
- **하지 말 것**: 논문에 없는 숫자, RQ, 기여, 한계를 지어내기.
- **하지 말 것**: URL / DOI / arXiv ID 조작 — 위 규칙 참조.
- **하지 말 것**: 실행 디렉토리에 무관한 다운로드를 남기지 마세요. 키워드 검색은 관련성 매칭이라 주제와 무관한 논문이 포함되곤 합니다("Claude code" 쿼리가 Viterbi 디코더 논문을 끌어왔고, "LLM code review" 가 객체 탐지 문헌 리뷰를 끌어왔습니다). 주제와 무관한 것으로 분류한 후 해당 `pdfs/<key>.pdf` 와 경량 `<key>.pptx` 를 삭제하세요. 집계된 xlsx / bib 는 검색이 반환한 것의 정직한 기록으로 유지하세요.
- **하지 말 것**: 커밋 메시지, PR 설명, 코드 주석, 문서에서 "Claude", "Claude Code", "AI-generated", "GPT", "Copilot" 등 AI 도구/모델 이름 언급.

## 기능

- **11 개 플러그인형 소스**: `arxiv`, `semantic_scholar`, `openalex`, `pubmed`, `acm` (Crossref 로 ACM 한정), `dblp`, `crossref` (일반), `openaire`, `springer` (API 키 필요), `ieee` (API 키 또는 스크래핑 opt-in), `scholar` (스크래핑 opt-in). 각각 `sources/<name>/` 아래에서 `Fetcher` 어댑터로 구현됩니다. 최상위급 출판처 화이트리스트가 기본적으로 결과를 주요 CS 학회/저널 + Nature/Science/PNAS 로 필터링하며, `--all-venues` 로 비활성화 가능.
- **단일 논문 모드**: arXiv ID, arXiv URL, DOI, PMID, 또는 IEEE 문서 URL 을 붙여 넣으면 AutoPaperToPPT 가 적절한 소스로 해당 논문을 가져와 동일한 내보내기 번들을 생성합니다. 논문 읽기 노트 및 학위 심사 준비에 유용.
- **로컬 PDF 모드** (`--pdf <경로>`): PDF 하나 또는 디렉토리를 전달. 휴리스틱 추출기가 각 PDF 의 앞부분에서 **제목, 저자, 연도, arXiv ID, DOI, 진짜 초록** 을 끌어냅니다 (명시적 `Abstract` / `ABSTRACT` / `摘要` 헤더에 고정, 임의 prefix 가 아님). 단일 PDF 호출에서는 `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` 가 override 합니다. 디렉토리 모드에서는 파일별 추출이 이깁니다 — 각 논문은 자신의 BibTeX 키 이름으로 덱이 생성됩니다.
- **5 개 내보내기**:
  - `.pptx` — 16:9 와이드스크린, 페이지 번호 부여, 3 가지 렌더링 계층 (라이트 초록만 · 강화-flat · **논문 발표 스타일** 페인 포인트 사분면, KPI 하이라이트, 기술 비교표, RQ 별 결과표, 기여 요약, 핵심 관찰, 한계 및 향후 작업, Q&A, 참고문헌). 모든 템플릿 문자열은 **14 개 언어** 로 i18n: English, 繁體中文, 简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - `.xlsx` — Papers 시트 + Query 출처 시트, URL / PDF 하이퍼링크, 헤더 고정, 자동 열 너비. 열 5 (**Source**) 는 실제 출판처 (예: "IEEE Access"), 열 6 (**Indexed via**) 는 메타데이터를 반환한 페처 (예: "openalex") 를 보여줘 두 정보가 충돌하지 않습니다.
  - `.md` — 전체 출처 / 제목 / 초록 리스트.
  - `.bib` — 충돌 없는 인용 키, LaTeX 이스케이프된 필드.
  - `.json` — 다운스트림 도구를 위한 원시 페이로드.
- **PPT 편집 툴킷**: `autopapertoppt.exporters.pptx_edit` (inspect / update_slide / delete_slide / reorder_slides / add_slide) 는 익스포터가 생성한 모든 덱에 대해 작동. 동등한 `pptx_*` MCP 도구로 LLM 에이전트가 생성된 덱을 반복적으로 수정 가능.
- **MCP 서버**: 11 개 도구 — `list_sources` (디스커버리), `search`, `fetch_paper`, `fetch_pdf_text`, `download_pdfs`, `export`, 그리고 5 개의 `pptx_*` 편집 도구. MCP 호환 LLM (Claude Code, Claude Desktop, Cursor, …) 이 전체 워크플로를 구동 가능.
- **두 가지 enrichment 경로** 초록을 넘어 진짜 논문 발표 스타일 덱으로:
  - **LLM-as-agent (API 키 불필요)** — 호출 LLM 이 `fetch_pdf_text` 로 PDF 본문을 읽고, 컨텍스트 내에서 구조화 요약을 작성, `export` 에 전달.
  - **Python 파이프라인 (`--enrich`)** — CLI 가 Anthropic API 를 직접 호출. 기본 모델 `claude-opus-4-7`.
- **기본 안전**: HTTPS-only HTTP 전송, 소스별 레이트 리미트 (토큰 버킷), 모든 XML 페이로드에 `defusedxml`, path-traversal 안전 내보내기 경로, 사용자 입력에 `eval` / `exec` / `pickle` 사용 안 함. Scholar 및 IEEE 스크래핑은 기본적으로 비활성 (env var opt-in).

## 빠른 시작

```powershell
git clone <repo-url>
cd AutoPaperToPPT
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# dev extras 와 함께 설치 (MCP SDK 와 intelligence deps 도 함께 들어옵니다)
pip install -e .[dev]
```

arXiv 검색하고 덱 + 워크북 + BibTeX 내보내기 (`--query` 기본):

```powershell
py -m autopapertoppt --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

URL 로 단일 논문 가져오기 — 기본 `.pptx + .bib` (한 행 `.xlsx` 는 의미가 적음):

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

덱을 한국어로 렌더링:

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --lang ko --out .\exports\
```

LLM 파이프라인 enrichment (Python 이 Anthropic 호출 — API 키 필요):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang ko --out .\exports\
```

## CLI 플래그

| 플래그 | 용도 |
|---|---|
| `--query` / `-q` | 키워드 (`--paper` 가 없으면 필수). |
| `--paper` / `-p` | arXiv ID / URL, DOI, PMID, 또는 IEEE 문서 URL. `--query` 와 상호 배타. |
| `--source` / `-s` | 쉼표로 구분된 소스 목록. 기본 `arxiv`. |
| `--max` / `-n` | 소스당 최대 결과 (1..200). 기본 25. |
| `--year-from` / `--year-to` | 양 끝 포함 연도 필터. |
| `--export` / `-e` | 포맷: `pptx,xlsx,md,bib,json` 중 임의. 기본은 모드에 따름 (아래 참조). |
| `--out` / `-o` | 출력 디렉토리. 기본 `./exports`. |
| `--filename-stem` | 생성되는 파일명 stem 을 override. |
| `--no-abstract` | 내보내기에서 초록 내용을 생략. |
| `--lang` / `-l` | 덱 언어: 14 개 중 하나 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. 기본 `en`. |
| `--enrich` | PDF 다운로드 + Anthropic 요약. `ANTHROPIC_API_KEY` 와 `[intelligence]` extra 필요. |
| `--lightweight` | `ANTHROPIC_API_KEY` 가 있어도 라이트 덱 강제. |
| `--llm-model` | enrichment 기본 `claude-opus-4-7` override. |
| `--all-venues` | 최상위 화이트리스트 비활성화 (기본은 주요 CS 출판처 + Nature / Science / PNAS / CACM / LNCS 유지). |
| `--paywall-threshold` | 확인 프롬프트를 트리거하는 paywall 결과 비율. 기본 0.30. |
| `--yes` | paywall 프롬프트 건너뜀. |
| `--max-slides` | 논문별 슬라이드 상한 (기본 25, 0 은 무제한). |
| `--quiet` | 논문별 출력 억제. |

### 환경 변수

| 변수 | 사용처 | 용도 |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | LLM 인증. MCP 위 LLM-as-agent 경로에서는 불필요. |
| `AUTOPAPERTOPPT_LLM_MODEL` | `--enrich` | 기본 `claude-opus-4-7` override. |
| `AUTOPAPERTOPPT_S2_API_KEY` | Semantic Scholar | 더 높은 레이트 리미트. 선택. |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | PubMed | NCBI 익명 한도 (3/s) 를 10/s 로 상향. 선택. |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex | 요청을 Crossref polite pool 에 넣음. |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | IEEE (API 경로) | 공식 IEEE Xplore API; 구독 범위 논문에 `pdf_url` 노출. |
| `AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING` | IEEE (스크래핑 경로) | `=1` 로 스크래핑 활성. API 키가 설정된 경우 불필요. |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Crossref Plus 구독자 토큰 (Bearer 헤더). 선택. |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | Springer | 필수; <https://dev.springernature.com/> 에서 무료 키. 없으면 플러그인이 조용히 건너뜀. |
| `AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING` | Google Scholar | `=1` 로 스크래핑 활성. 기본 비활성 — Scholar ToS 가 스크래핑 금지. |
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | PDF 다운로더 | Netscape 형식 `cookies.txt`. 기본 비활성. 기관 접근 권한이 있는 출판사에만 사용하세요. |
| `AUTOPAPERTOPPT_LOG_LEVEL` | logger | 기본 `INFO`; verbose 추적은 `DEBUG`. |

기본: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. 명시적 `--export` 로 항상 override 가능.

## MCP 서버

Claude Code 에 등록:

```powershell
claude mcp add autopapertoppt -- ".venv\Scripts\python.exe" -m autopapertoppt.mcp
```

또는 설정 파일을 편집:

```json
{
  "mcpServers": {
    "autopapertoppt": {
      "command": ".venv\\Scripts\\python.exe",
      "args": ["-m", "autopapertoppt.mcp"]
    }
  }
}
```

도구:

| 도구 | 용도 |
|---|---|
| `list_sources` | 모든 플러그인 열거 + 현재 env 에서 각각 활성화 여부 보고. `search` 전에 한 번 호출. |
| `search` | 키워드 → 논문 목록. `top_tier_only`, `min_citations` 수용; `sources` 미지정시 API 키 불필요 소스 전체 기본. |
| `fetch_paper` | arXiv / DOI / PMID / IEEE 식별자 → 단일 논문. |
| `fetch_pdf_text` | 단일 PDF 다운로드, 추출된 본문 반환. **MCP 경유 "논문을 읽었음" 진입점.** |
| `download_pdfs` | 논문 목록의 PDF 를 `{out_dir}/pdfs/` 에 일괄 다운로드. BibTeX 키로 인덱싱된 논문별 결과 반환. |
| `export` | 논문 목록 + 포맷 → `.pptx/.xlsx/.md/.bib/.json` 작성. 논문별 `summary` 필드 (논문 발표 스타일 스키마) 와 `max_slides_per_paper` (기본 25) 수용. |
| `pptx_inspect` | 기존 덱의 슬라이드 / 셰이프 구조 읽기. |
| `pptx_update_slide` | `title` / `body` / `meta` (셰이프 이름으로) 또는 임의 셰이프 (인덱스로) 교체. |
| `pptx_delete_slide` | 슬라이드와 그 part relationship 제거. |
| `pptx_reorder_slides` | `sldIdLst` 경유 슬라이드 재정렬. |
| `pptx_add_slide` | 새 title / body / meta 슬라이드를 끝에 추가 또는 지정 위치에 삽입. |

LLM-as-agent 플로우 (`ANTHROPIC_API_KEY` 불필요 — LLM 자체가 에이전트):

```
1. (선택) list_sources()                           # 활성 플러그인 발견
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (선택) download_pdfs(papers, out_dir="./exports/...")  # PDF 영속화
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # 논문별
5. (LLM 이 본문을 읽고 구조화된 `summary` dict 생성)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="ko", formats=["pptx","bib"], ...)
```

전체 참조는 [`docs/mcp.md`](docs/mcp.md).

## 프로젝트 구조

```
AutoPaperToPPT/
├── autopapertoppt/                 # 메인 패키지
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # HTTPS-only async 클라이언트, 토큰 버킷 레이트 리미트
│   ├── exporters/                   # pptx (논문 발표 스타일) · xlsx · bib · md · json · pptx_edit · i18n
│   ├── intelligence/                # PDF 다운로드 + Anthropic 요약기 ([intelligence] extra)
│   ├── mcp/                         # FastMCP 서버 (11 도구)
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # argparse CLI
│   └── __main__.py
├── sources/                         # 플러그인 폴더: arxiv, semantic_scholar,
│                                    #   openalex, pubmed, acm, ieee, scholar,
│                                    #   dblp, crossref, openaire, springer
├── tests/                           # pytest 스위트 + 녹화된 fixture (live HTTP 없음)
├── docs/                            # Sphinx (14 개 언어 트리)
├── scripts/                         # 일회용 regen 스크립트
└── pyproject.toml                   # ruff, bandit, build, 선택 extras
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r autopapertoppt/ sources/
```

bandit 의 `-c` 플래그는 필수 — 없으면 bandit 가 프로젝트 skip 설정을 무시합니다. pptx 익스포터를 건드릴 때는 overflow 검사도 실행 (`CLAUDE.md` "Slide Deck Rules" 참조).

## 라이선스

`LICENSE` 참조. arXiv API 는 arXiv 약관 (<https://info.arxiv.org/help/api/tou.html>) 에 따라 사용 — 3 초당 1 요청의 소프트 한계 준수; 포함된 페처가 token bucket 을 통해 이를 이미 강제합니다.

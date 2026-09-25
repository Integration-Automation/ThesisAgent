# ThesisAgents

[![CI](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/ThesisAgents/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![Python](https://img.shields.io/pypi/pyversions/thesisagents.svg)](https://pypi.org/project/thesisagents/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/ThesisAgents.svg)](https://github.com/Integration-Automation/ThesisAgents/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/thesisagents/badge/?version=latest)](https://thesisagents.readthedocs.io/en/latest/)

> **언어**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · **한국어** · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **문서**: [thesisagents.readthedocs.io](https://thesisagents.readthedocs.io/en/latest/)

arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (Crossref 경유), IEEE
Xplore, DBLP, 일반 Crossref, OpenAIRE, Springer Nature, Europe PMC,
DOAJ, HAL, CORE, Google Scholar 에서 결과를 가져와 하나의 레코드
형식으로 정규화하고, 중복 제거된 집합을 **논문 스타일 PowerPoint
슬라이드**, **Excel 워크북**, **BibTeX 파일** 로 내보내는 키워드 기반
논문 검색 어시스턴트 — 모두 하나의 CLI 호출 또는 하나의 MCP 도구
호출로 처리됩니다. 선택적으로 각 논문의 PDF 를 읽어 논문별 구조화
요약을 컨텍스트 내(LLM-as-agent 경로)에서 또는 Anthropic API(Python
파이프라인 경로)를 통해 생성하여 각 논문을 보강합니다.

## 이 프로젝트를 구동하는 AI 에이전트를 위해

**당신이 LLM(Claude Code, Cursor, Aider, Codex CLI, …)이고 무엇을
해야 하는지 파악하기 위해 이 README 를 읽고 있다면 — 여기서
시작하세요.** 아래 내용은 모두 [`AGENTS.md`](../AGENTS.md)(교차 에이전트
미러)와 [`CLAUDE.md`](../CLAUDE.md)(정본 레퍼런스)에도 고정되어 있으니,
사소하지 않은 변경을 하기 전에 먼저 읽으세요.

### 사용자가 실제로 원하는 것

기본 산출물은 **논문별 논문 스타일의 리치 `.pptx`** 이지, CLI 가
기본으로 만들어 내는 초록만 담은 경량 덱이 아닙니다. 경량 출력물은
중간 산출물이며 — 이를 업그레이드하는 것이 당신의 역할입니다.

### 결정 트리

1. 환경에 `ANTHROPIC_API_KEY` 가 설정되어 있는가? → CLI 를 그냥
   실행하세요. Anthropic API 를 통해 자동으로 보강합니다. 끝.
2. 키는 없지만 당신(LLM)이 세션을 구동하고 있다면 → **리치 요약을
   직접 생성하세요.** 각 PDF 를 읽고, 리치 티어 필드
   (`pain_points`, `research_question`, `contributions_detailed`,
   `headline_metrics`, `technique_table`, `method_sections`,
   `evaluation_sections`, `system_flow`, `research_questions`,
   `rq_results`, `core_observation`, `limitations`, `future_work`)를
   갖춘 `PaperSummary` 를 직접 작성하고, `scripts/regen_<query>.py` 를
   두고 실행하세요. **사용자에게 API 키를 설정하라고 말하지 마세요** —
   요약을 작성했을 LLM 이 바로 당신입니다.
3. 루프에 LLM 이 없다면(CI / cron / 무인) → 경량으로 충분합니다.

### 6단계 MCP 워크플로

```
1. (optional) list_sources()                              # see which plugins are enabled
2. search(keywords, sources, top_tier_only=true, ...)
3. (optional) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # per paper
5. (you read each PDF and produce a structured summary dict)
6. export(papers=[{...paper, "summary": {...}}], language="zh-tw", ...)
```

열세 개의 MCP 도구 전체(`list_sources`, `list_exports`,
`download_pdfs`, `pptx_inspect` / `pptx_review` / `pptx_update_slide` /
`pptx_add_slide` / 등 포함)는 [`docs/mcp.md`](../docs/mcp.md)에
문서화되어 있습니다.

### 필수: 배포 전 URL / DOI 검증

퍼블리셔 URL 경로는 **추측할 수 없습니다** — AAAI 는 숫자 ID
(`v40i5.37389`)를, IEEE 는 불투명한 `arnumber` 를, ACM 은 불투명한
DOI 를 사용합니다. `Paper` 를 직접 작성할 때는 **이 실행을 만들어 낸
검색 xlsx 에서 `url` / `doi` / `arxiv_id` 를 그대로 복사하세요** —
기억에 의존하지 말고, 제목으로부터 구성하지 마세요.

xlsx 는 `exports/<run>/<slug>-<timestamp>.xlsx` 에 쓰이며, 7번 열 =
DOI, 8번 열 = URL 입니다. 끝나면 regen 스크립트를 감사하세요:

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

이 방법으로 프로덕션에서 잡아낸 두 건의 조작: 잘못된 AAAI 권 번호
(`v39i23.34521` vs 실제 `v39i22.34537`)와 지어낸 저자 슬러그 경로
(`view/fang2026` 대신 `v40i5.37389`).

### 필수: 배포 전 무관한 다운로드 정리

검색 키워드 매칭은 키워드 기반이므로 주제에서 벗어난 논문이 섞여
들어옵니다: "Claude code" 쿼리가 둘 다 "code" 를 포함한다는 이유로
Viterbi 디코더 논문을 반환했고, "LLM code review" 가 객체 탐지 문헌
리뷰에 매칭되었습니다. 초록을 읽고 어떤 논문이 사용자의 실제 의도에
비추어 주제에서 벗어났다고 분류하면, 실행 디렉터리를 정리하세요:

```python
from pathlib import Path
run = Path("exports/<run>")
irrelevant_keys = ("key-of-off-topic-paper-1", "key-of-off-topic-paper-2")
for key in irrelevant_keys:
    for path in (run / "pdfs" / f"{key}.pdf", run / f"{key}.pptx"):
        if path.exists():
            path.unlink()
```

`exports/<run>/pdfs/<key>.pdf` + `exports/<run>/<key>.pptx` 를
삭제하세요. 집계 `<slug>-<timestamp>.xlsx` / `.bib` 는 **유지하세요**
— 이것들은 검색이 무엇을 반환했는지에 대한 정직한 기록입니다.
경계선상의 경우에는 리치 요약을 부여하세요. 가능한 매칭을 조용히
버리는 것보다 과하게 포함하는 편이 낫습니다.

### 작동 예시

[`scripts/regen_fang2026.py`](../scripts/regen_fang2026.py)는 정확히 이
방식으로 만들어진 직접 작성한 리치 요약을 제공합니다(단일 논문,
리치 티어, zh-tw, 모든 리치 필드가 채워짐). 다중 논문 검색은
`PaperCollection` 튜플 안에 논문마다 하나의
`Paper(...summary=PaperSummary(...))` 항목을 두는 같은 형태를
따릅니다.

### 하지 말 것

- 다중 논문 검색을 끝내면서 사용자에게 "리치 덱을 위해
  `ANTHROPIC_API_KEY` 를 설정하라"고 **말하지 마세요** — 요약을
  작성했을 수 있는 LLM 이 바로 당신입니다.
- 논문별 경량 `.pptx` 를 산출물로 **취급하지 마세요**.
- `download_pdfs` 가 N 개의 PDF 를 저장했다고 보고한 뒤에
  **멈추지 마세요** — 그것은 리치 저작 단계의 시작이지 끝이
  아닙니다.
- 논문에 없는 숫자, RQ, 기여, 한계를 **지어내지 마세요**.
- URL / DOI / arXiv ID 를 **조작하지 마세요** — 위의 규칙을 보세요.
- 무관한 다운로드를 실행 디렉터리에 **남겨두지 마세요**. 키워드
  검색 매칭은 주제에서 벗어난 논문을 포함할 수 있습니다("Claude
  code" 쿼리가 Viterbi 디코더 논문을 끌어들였고, "LLM code review"
  가 객체 탐지 문헌 리뷰를 끌어들였습니다). 논문을 주제에서
  벗어난 것으로 분류한 뒤에는 그것들의 `pdfs/<key>.pdf` 와 경량
  `<key>.pptx` 를 삭제하고, 검색이 무엇을 반환했는지에 대한 정직한
  기록으로서 집계 xlsx / bib 는 유지하세요.
- 커밋 메시지, PR 설명, 코드 주석, 문서 어디에도 "Claude",
  "Claude Code", "AI-generated", "GPT", "Copilot" 또는 어떤 AI
  도구/모델 이름도 **언급하지 마세요**.

## 기능

- **플러그형 소스 15종**: `arxiv`, `semantic_scholar`, `openalex`,
  `pubmed`, `acm`(Crossref 범위), `dblp`, `crossref`(비범위),
  `openaire`, `springer`(API 키 필요), `europepmc`(공개, 키 불필요 —
  생명과학 + 프리프린트 + 농업), `doaj`(공개, 키 불필요 — 오픈
  액세스 저널, 보통 직접 PDF 링크 포함), `hal`(공개, 키 불필요 —
  프랑스의 CS / 수학 / 물리 아카이브, 전문 PDF 포함), `core`(무료
  API 키 필요 — 최대 규모의 오픈 액세스 애그리게이터, 2.5억+ 저작물),
  `ieee`(가시 Chrome 을 통해 기본 활성화, API 키는 공식 Xplore API
  추가), `scholar`(가시 Chrome 을 통해 기본 활성화). 각각은
  `sources/<name>/` 에 `Fetcher` 어댑터 뒤에 존재합니다.
  `--top-tier-only` 를 넘기면 결과를 대표 CS 학회/저널에 Nature /
  Science / PNAS 를 더한 범위로 필터링합니다. 기본 검색은 모든 발표처를
  유지합니다.
- **단일 논문 모드**: arXiv ID, arXiv URL, DOI, PMID 또는 IEEE 문서
  URL 을 붙여넣으면 — ThesisAgents 가 올바른 소스를 통해 해석하고
  동일한 내보내기 번들을 생성합니다. 논문 읽기 노트와 논문 심사 준비에
  유용합니다.
- **로컬 PDF 모드**(`--pdf <path>`): 하나의 PDF 또는 디렉터리를
  넘깁니다. 휴리스틱 추출기가 각 PDF 의 앞부분에서 **제목, 저자, 연도,
  arXiv ID, DOI, 실제 초록** 을 곧바로 뽑아냅니다(맹목적인 접두 부분이
  아니라 명시적인 `Abstract` / `ABSTRACT` / `摘要` 헤더에 고정).
  단일 PDF 호출에서는 `--title` / `--authors` / `--year` / `--venue` /
  `--doi` / `--arxiv-id` 가 덮어씁니다. 디렉터리에서는 파일별 추출이
  우선하므로 모든 논문이 자신의 BibTeX 키로 이름 붙은 자기만의 덱을
  갖습니다.
- **내보내기 8종**:
  - `.pptx` — 16:9 와이드스크린, 페이지 번호 부여, 세 가지 렌더링
    티어(경량 초록 전용 · 보강-평면 · **논문 스타일** — 페인
    포인트 사분면, KPI 콜아웃, 기법 비교표, RQ별 결과표, 기여 요약,
    핵심 관찰, 한계 및 향후 과제, Q&A, 참고문헌 포함). 모든 템플릿
    문자열은 **14개 언어** 로 i18n 되어 있습니다: English, 繁體中文,
    简体中文, 日本語, Español, Français, Deutsch, 한국어, Português,
    Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia.
  - **디자인된 덱의 시각적 아이덴티티**(기본 Calibri-on-white
    모습이 아님): 언어별 타이포그래피(라틴에는 Inter, CJK + 힌디에는
    Microsoft JhengHei UI / YaHei UI / Yu Gothic UI / Malgun Gothic /
    Nirmala UI), 프로그래밍적 액센트 지오메트리(모든 콘텐츠
    슬라이드 상단의 액센트 바 + 표지의 좌측 밴드), 학술 스타일 표
    서식(기본 그리드 제거, 네이비 헤더 룰, 부드러운 행간 구분선,
    교대 행 줄무늬, 세로 중앙 정렬, 굵은 행 레이블), 그리고 텍스트에
    빨강을 **금지** 한 5색 팔레트 규율(네이비 / 틸 / 그레이 / 라이트 /
    화이트) — 강조에는 대신 굵게 + 틸 `#0E7490` 를 사용.
  - **라이트 모드가 기본 렌더링 경로입니다.** `--dark-mode` 를
    넘기거나, GUI Deck 탭에서 **Dark mode** 를 활성화하거나,
    `ExportOptions(dark_mode=True)` 를 설정하면 다크 후처리를
    적용합니다(슬라이드 배경 `#12151B`, 본문 텍스트 `#E5E7EB`).
  - `.xlsx` — Papers 시트 + Query 출처 시트, URL / PDF 하이퍼링크,
    고정 헤더, 자동 열 너비. 5번 열(**Source**)은 실제 출판
    발표처(예: "IEEE Access")를, 6번 열(**Indexed via**)은 어느
    페처가 메타데이터를 반환했는지(예: "openalex")를 표시하므로 두
    정보가 결코 충돌하지 않습니다.
  - `.md` — 전체 소스 / 제목 / 초록 목록.
  - `.bib` — 충돌 없는 인용 키, LaTeX 이스케이프된 필드.
  - `.json` — 다운스트림 도구를 위한 원시 페이로드.
  - `.ris` — Zotero / Mendeley / EndNote / RefWorks 가 가져오는 RIS
    교환 형식(비-LaTeX 레퍼런스 매니저를 위한 BibTeX 의 형제).
  - `.csv` — 스프레드시트 / 빠른 grep 분류를 위한 논문당 한 행의
    평면 표(RFC-4180 인용, 제목 안의 쉼표가 열을 밀지 않음).
  - `.csl.json` — Pandoc / citeproc 를 위한 CSL-JSON; 임의의 CSL
    스타일(APA, IEEE, Nature, …)로 참고문헌을 렌더링. `.csl.json`
    확장자는 이를 일반 `.json` 덤프와 구별해 줍니다.
- **PPT 편집 툴킷**: `thesisagents.exporters.pptx_edit`
  (inspect / update_slide / delete_slide / reorder_slides /
  add_slide)는 내보내기가 만들어 낸 어떤 덱에도 작동하며, 여기에
  더해 동등한 `pptx_*` MCP 도구가 있어 LLM 에이전트가 생성된 덱을
  반복 개선할 수 있습니다.
- **MCP 서버**: 13개 도구 — `list_sources` + `list_exports`
  (탐색), `search`, `fetch_paper`, `fetch_pdf_text`,
  `download_pdfs`, `export`, 그리고 여섯 개의 `pptx_*` 덱 도구
  (`inspect`, `review`, `update_slide`, `delete_slide`,
  `reorder_slides`, `add_slide`). MCP 를 인식하는 어떤 LLM
  (Claude Code, Claude Desktop, Cursor, …)이든 전체 워크플로를
  구동할 수 있게 합니다.
- **초록을 넘어 진정한 논문 스타일 덱으로 가기 위한 두 가지 보강
  경로**:
  - **LLM-as-agent(API 키 불필요)** — 호출하는 LLM 이
    `fetch_pdf_text` 를 통해 PDF 본문 텍스트를 읽고, 컨텍스트 내에서
    구조화 요약을 작성해 `export` 에 넘깁니다.
  - **Python 파이프라인(`--enrich`)** — CLI 가 스스로 Anthropic 의
    API 를 호출합니다. 기본 모델 `claude-opus-4-7`.
- **가시 Chrome 퍼블리셔 흐름**: Scholar SERP, IEEE `/rest/search`,
  그리고 모든 페이월 PDF 다운로드(ieeexplore / dl.acm / link.springer
  / sciencedirect / wiley / oup / nature / science / …)는 `selenium`
  을 통해 실제 가시 Chrome 세션 안에서 실행됩니다. 사용자는 라이브
  창에서 캡차를 풀거나 SSO 를 한 번 완료하고,
  `THESISAGENTS_CHROME_PROFILE_DIR` 이 실행 간에 쿠키를 유지합니다.
- **LLM-as-agent 흐름**: MCP 도구가 검색, PDF 다운로드, 텍스트
  추출을 제공합니다. `scripts/regen_*.py` 는 논문별 리치
  `PaperSummary` 를 직접 작성하기 위한 재현 가능한 예시를 담고
  있습니다.
- **OA PDF 리졸버**: 중복 제거 후, `pdf_url` 이 없는 모든 논문은
  Unpaywall → S2 `openAccessPdf` → arXiv 제목 검색 →
  CORE.ac.uk(키가 설정된 경우)를 거칩니다. IEEE / ACM / Springer /
  Elsevier 가 많은 쿼리에서의 전형적인 향상: 40-70 퍼센트 포인트.
- **기본값이 안전**: HTTPS 전용 HTTP 전송, 소스별 속도 제한(토큰
  버킷), 모든 XML 페이로드에 `defusedxml`, 경로 순회에 안전한
  내보내기 경로, 사용자 입력에 대한 `eval` / `exec` / `pickle` 없음.
- **zh-tw / zh-cn 어휘 가드**:
  `tests/test_i18n.py::test_zh_tw_files_use_traditional_chinese_vocabulary`
  안의 약 244개 정규식 패턴이 번체 한자로 렌더링된 간체 중국어 차용어
  (예: `內存` → `記憶體`, `魯棒性` → `穩健性`, `軟件` → `軟體`,
  `緩存` → `快取`)를 잡아냅니다. zh-cn 로케일 문자열에 대해서도 같은
  가드가 역방향으로 실행됩니다. 전체 규칙 + 정규식 카탈로그는
  `.claude/agents/rules/language-vocabulary-check.md` 에 있습니다.

## 빠른 시작

```powershell
git clone <repo-url>
cd ThesisAgents
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# Install with dev extras (also pulls in MCP SDK and intelligence deps)
pip install -e .[dev]
```

arXiv 를 검색하고 덱 + 워크북 + BibTeX 를 내보내기(`--query` 의
기본값):

```powershell
py -m thesisagents --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

URL 로 단일 논문 가져오기 — 기본은 `.pptx + .bib`(한 행에는 `.xlsx`
가 별로 의미 없음):

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

덱을 繁體中文 로 렌더링:

```powershell
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --lang zh-tw --out .\exports\
```

LLM 파이프라인 보강(Python 이 직접 Anthropic 을 호출 — API 키 필요):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m thesisagents --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang zh-tw --out .\exports\
```

## CLI 플래그

| 플래그 | 용도 |
|---|---|
| `--query` / `-q` | 키워드(`--paper` 가 없으면 필수). |
| `--paper` / `-p` | arXiv ID / URL, DOI, PMID 또는 IEEE 문서 URL. `--query` 와 상호 배타적. |
| `--source` / `-s` | 쉼표로 구분된 소스 목록. 기본 `arxiv`. |
| `--max` / `-n` | 소스당 최대 결과 수(1..200). 기본 25. |
| `--year-from` / `--year-to` | 포함 연도 필터. |
| `--export` / `-e` | 형식: `pptx,xlsx,md,bib,json,ris,csv,csl` 중 아무거나. 기본은 모드에 따라 다름(아래 참고). |
| `--out` / `-o` | 출력 디렉터리. 기본 `./exports`. |
| `--filename-stem` | 생성되는 파일명 어간을 덮어씀. |
| `--no-abstract` | 내보내기에서 초록 내용을 생략. |
| `--lang` / `-l` | 덱 언어: 14개 중 하나 — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`. 기본 `en`. |
| `--enrich` | 자동 보강의 실패-표출 변형. `ANTHROPIC_API_KEY` 와 `[intelligence]` extra 가 필요. (키가 설정되면 자동 보강이 기본.) |
| `--lightweight` | 보강을 건너뛰고 초록 전용 덱을 강제. 빠른 / 무인 실행에만 사용. **LLM 에이전트가 구동 중이라면 아래의 LLM-as-agent 흐름을 선호하세요.** |
| `--llm-model` | 보강 시 기본 `claude-opus-4-7` 을 덮어씀. |
| `--no-pdf` | 자동 PDF 다운로드를 건너뜀. 논문별 PPT 게이트도 비활성화(PDF 없음 → 전체 내용 없음). |
| `--no-oa-resolve` | 중복 제거 후 OA PDF 리졸버(Unpaywall + S2 + arXiv + CORE.ac.uk)를 건너뜀. |
| `--top-tier-only` | 결과를 arXiv + 엄선된 CS 대표 화이트리스트(S&P, CCS, NDSS, USENIX Security, NeurIPS, ICML, ICSE, …)로 제한. 기본 꺼짐. |
| `--paywall-threshold` | 확인 프롬프트를 촉발하는 페이월 결과의 비율. 기본 0.30. |
| `--yes` | 페이월 프롬프트를 건너뛰고 진행. |
| `--max-slides` | 논문당 슬라이드 상한(기본 25; 무제한은 0 을 넘김). |
| `--dark-mode` | pptx 를 어두운 배경 + 거의 흰 텍스트로 렌더링. 기본은 라이트 네이비 밴드 덱. |
| `--quiet` | 논문별 출력을 억제. |

### 환경 변수

| 변수 | 사용 주체 | 용도 |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | LLM 인증. MCP 상의 LLM-as-agent 경로에는 불필요. |
| `THESISAGENTS_LLM_MODEL` | `--enrich` | 기본 `claude-opus-4-7` 을 덮어씀. |
| `THESISAGENTS_S2_API_KEY` | Semantic Scholar + OA 리졸버 | 더 높은 속도 제한; OA 리졸버의 S2 `openAccessPdf` 단계에서도 사용. 무료 키는 <https://www.semanticscholar.org/product/api> 에서. |
| `THESISAGENTS_NCBI_API_KEY` | PubMed | NCBI 의 익명 제한(3/s)을 10/s 로 올림. 선택 사항. |
| `THESISAGENTS_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex, **Unpaywall** | 폴라이트-풀 태그 + OA 리졸버의 Unpaywall 단계를 활성화(IEEE / ACM / Springer / Elsevier 페이월 논문의 PDF 커버리지에서 가장 큰 이득; 전형적 향상 40-70 pp). |
| `THESISAGENTS_IEEE_API_KEY` | IEEE(API 경로) | 공식 IEEE Xplore API; 범위 내 논문의 `pdf_url` 을 표출. |
| `THESISAGENTS_DISABLE_IEEE_SCRAPING` | IEEE | **IEEE 는 가시 Chrome 을 통해 기본 켜짐.** `=1` 로 설정하면 옵트아웃(예: Chrome 없는 CI). httpx 스크레이프 분기는 WebRunner 를 사용할 수 없을 때 폴백으로만 실행. |
| `THESISAGENTS_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Crossref Plus 구독자 토큰(Bearer 헤더). 선택 사항. |
| `THESISAGENTS_SPRINGER_API_KEY` | Springer | 필수; 무료 키는 <https://dev.springernature.com/> 에서. 없으면 플러그인이 `ConfigError` 발생. |
| `THESISAGENTS_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | **Scholar 는 가시 Chrome 을 통해 기본 켜짐.** `=1` 로 설정하면 옵트아웃(Google 의 ToS 가 자동 접근을 금지 — 커버리지를 위해 기본 켜짐, 캡차 / IP 차단 위험을 피하려면 옵트아웃). |
| `THESISAGENTS_CHROME_PROFILE_DIR` | Scholar + IEEE + 페이월 PDF 다운로드 | 영속 Chrome `--user-data-dir`. 이것을 설정하고 VPN / SSO / Google 로그인을 한 번 완료하면; 이후 실행이 쿠키를 상속하여 IEEE 가 페이월 메타데이터를 반환하고 Scholar 가 스로틀 없는 SERP 를 제공. |
| `THESISAGENTS_DISABLE_WEBRUNNER` | Scholar + IEEE + 페이월 PDF 다운로드 | `=1` 은 실제 Chrome 을 구동하는 대신 httpx 경로를 강제. Chrome 바이너리가 없는 CI / Docker 에 유용; 그 외에는 설정하지 않은 채로. |
| `THESISAGENTS_CORE_API_KEY` | OA 리졸버 + `core` 검색 소스 | 무료 키는 <https://core.ac.uk/services/api> 에서. CORE.ac.uk OA 조회 단계(2억+ 기관 / 지역 OA 항목) **및** `core` 검색 소스를 활성화. 없으면 `core` 소스는 조용히 건너뛰고 다른 OA 전략(Unpaywall, S2, arXiv)은 여전히 실행. |
| `THESISAGENTS_PDF_COOKIES_FILE` | PDF 다운로더 | Netscape `cookies.txt`. 기본 꺼짐. 기관 권한이 있는 퍼블리셔에만 사용. |
| `THESISAGENTS_LOG_LEVEL` | 로거 | 기본 `INFO`; 상세 추적에는 `DEBUG`. |

기본값: `--query` → `pptx,xlsx,bib`. `--paper` → `pptx,bib`. 언제나
명시적 `--export` 로 덮어쓸 수 있습니다.

## LLM-as-agent 흐름

에디터의 LLM 이 워크플로를 구동할 때는 MCP 도구를 순서대로
사용하세요: `search`, `download_pdfs`, `fetch_pdf_text`, 그다음 직접
작성한 리치 `PaperSummary` 로 `export`. 기존 `scripts/regen_*.py`
파일들은 최종 저작 및 내보내기 단계를 위한 재현 가능한 예시입니다.

검색 → 리치 덱까지의 전체 엔드투엔드 런북은
`.claude/agents/tasks/paper-summary-author.md` 에 있습니다 — 새
쿼리를 시작하기 전에 이를 열어두면 LLM 이 사용자 입력을 기다리며
멈추지 않고 흐름을 실행할 수 있습니다.

## MCP 서버

Claude Code 에 등록:

```powershell
claude mcp add thesisagents -- ".venv\Scripts\python.exe" -m thesisagents.mcp
```

또는 설정 파일에 작성:

```json
{
  "mcpServers": {
    "thesisagents": {
      "command": ".venv\\Scripts\\python.exe",
      "args": ["-m", "thesisagents.mcp"]
    }
  }
}
```

도구:

| 도구 | 용도 |
|---|---|
| `list_sources` | 모든 플러그인을 열거 + 현재 환경에서 각각이 활성인지 보고. `search` 전에 한 번 호출. |
| `list_exports` | 모든 내보내기 형식을 한 줄 설명과 함께, 그리고 그것이 하나의 집계 파일을 쓰는지 논문당 하나의 파일을 쓰는지 열거. |
| `search` | 키워드 → 논문 목록. `top_tier_only`, `min_citations` 를 받으며; 기본은 API 키 없는 전체 소스 믹스. |
| `fetch_paper` | arXiv / DOI / PMID / IEEE 식별자 → 단일 논문. |
| `fetch_pdf_text` | 하나의 PDF 를 다운로드하여 추출한 본문 텍스트를 반환. **"내가 논문을 읽었다"에 이르는 MCP 경로.** |
| `download_pdfs` | 논문 목록의 PDF 를 `{out_dir}/pdfs/` 로 일괄 다운로드. BibTeX 키로 키가 지정된 논문별 결과를 반환. |
| `export` | 논문 목록 + 형식 → `.pptx/.xlsx/.md/.bib/.json/.ris/.csv/.csl.json` 을 작성. 리치 논문 스타일 스키마를 위한 논문당 `summary` 필드, `max_slides_per_paper`(기본 25), `dark_mode`(기본 `false` — 프로젝트 기본은 라이트 네이비 밴드 덱, 어두운 OLED / 저조도 후처리에는 `true`)를 받음. |
| `pptx_inspect` | 기존 덱의 슬라이드 / 셰이프 구조를 읽음. |
| `pptx_review` | 한 번의 호출로 덱을 감사 — 오버플로 + 색상 계약 + `paper_rule` 섹션 완전성. 덱 언어를 자동 감지; CLI `python -m thesisagents review <deck.pptx>` 이기도 함. |
| `pptx_update_slide` | `title` / `body` / `meta`(셰이프 이름으로) 또는 인덱스로 임의의 셰이프를 교체. |
| `pptx_delete_slide` | 슬라이드와 그 파트 관계를 제거. |
| `pptx_reorder_slides` | `sldIdLst` 를 통해 슬라이드를 순열. |
| `pptx_add_slide` | 새 title / body / meta 슬라이드를 추가하거나 삽입. |

LLM-as-agent 흐름(`ANTHROPIC_API_KEY` 불필요 — LLM 이 에이전트):

```
1. (optional) list_sources()                       # discover enabled plugins
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (optional) download_pdfs(papers, out_dir="./exports/...")  # persist PDFs
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # per paper
5. (the LLM reads body text, produces a structured `summary` dict)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="zh-tw", formats=["pptx","bib"], dark_mode=true, ...)
```

전체 레퍼런스는 [`docs/mcp.md`](../docs/mcp.md) 에 있습니다.

## 프로젝트 구성

```
ThesisAgents/
├── thesisagents/                 # main package
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # HTTPS-only async client, token-bucket rate limit
│   ├── exporters/                   # pptx (thesis-style) · xlsx · bib · md · json · ris · csv · csl · pptx_edit · i18n
│   ├── intelligence/                # PDF fetch + Anthropic summariser  ([intelligence] extra)
│   ├── evaluation/                  # offline search-quality benchmark (docs/search-quality.md)
│   ├── mcp/                         # FastMCP server (13 tools)
│   ├── sources/<name>/              # plugin folders: arxiv, semantic_scholar,
│   │                                #   openalex, pubmed, acm, ieee, scholar,
│   │                                #   dblp, crossref, openaire, springer,
│   │                                #   europepmc, doaj, hal, core
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # argparse CLI
│   └── __main__.py
├── tests/                           # pytest suite + recorded fixtures (no live HTTP)
├── docs/                            # Sphinx (14 language trees)
├── scripts/                         # one-off regen scripts
└── pyproject.toml                   # ruff, bandit, build, optional extras
```

## 완료의 정의

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r thesisagents/
```

bandit 의 `-c` 플래그는 필수입니다 — 없으면 bandit 이 프로젝트 스킵
설정을 무시합니다. pptx 내보내기를 건드릴 때는 오버플로 검사도
실행하세요(`CLAUDE.md` "Slide Deck Rules" 참고).

## 데스크톱 GUI (PySide6)

네이티브 데스크톱 인터페이스가 `[gui]` extra 뒤에 제공됩니다:

```powershell
pip install thesisagents[gui]
thesisagents-gui                 # or: thesisagents gui
```

창에는 네 개의 탭이 있습니다 — **Search**, **Settings**(QSettings 를
통해 API 키를 영속화), **Enrich**(`collection_ready` 시그널을 통해
LLM-as-agent / Python 파이프라인 보강을 구동), 그리고 **Deck**(Light
모드 토글 + 슬라이드 상한 + 최대 figure 컨트롤이 `ExportOptions` 로
흘러 들어감). Windows 릴리스 zip 은 PySide6 를 포함한 Nuitka 컴파일
번들을 제공하므로, 별도의 Python 설치 없이 `thesisagents.exe gui` 가
동작합니다.
**UI 는 14개 언어 모두로 제공됩니다**(English, 繁體中文, 简体中文,
日本語, Español, Français, Deutsch, 한국어, Português, Русский,
Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia) — 첫 실행은 OS
로케일에서 언어를 고르고, 이후 **Settings → Interface language** 에서
바꿀 수 있습니다. 덱 출력 언어는 별도의 드롭다운이라 UI 를 한
언어로 실행하면서 슬라이드는 다른 언어로 낼 수 있습니다. 레이아웃은
반응형입니다: 모든 폼이 `QScrollArea` 안에 있고 창은 900×600 까지
줄어들며(720p 에도 여전히 맞음), HiDPI 스케일링이 기본으로
켜져 있습니다.

전체 레퍼런스: [`docs/gui.md`](../docs/gui.md).

## 독립 실행형 바이너리로 패키징

Python 설치 없이 실행되는 단일 파일 바이너리를 배포하기 위한 두
패키저가 문서화되어 있습니다:

- **[`docs/packaging-pyinstaller.md`](../docs/packaging-pyinstaller.md)**
  — 빠른 빌드(1분 미만), 200–300 MB 출력, 2–4초 시작. 빌드
  스크립트를 반복 개선할 때 최적.
- **[`docs/packaging-nuitka.md`](../docs/packaging-nuitka.md)** —
  느린 빌드(5–15분), 80–150 MB 출력, 1초 미만 시작, 약간의 바이트
  코드 보호. 최종 사용자가 바이너리를 여러 번 실행할 때 최적.

두 문서 모두 프로젝트 고유의 함정 — `sources/<name>/` 아래의 동적
소스 플러그인 — 을 다루며, CLI 와 MCP 서버 진입점에 대해 검증된
명령을 제공합니다.

## 지속적 통합 및 릴리스

두 개의 GitHub Actions 워크플로가 `.github/workflows/` 아래에
있습니다:

- **`ci.yml`** 은 `main` 에 대한 모든 푸시와 PR 에서 실행됩니다.
  매트릭스는 Ubuntu + Windows × Python 3.12 / 3.13 / 3.14(6개 잡).
  각 잡은 `ruff check`, `bandit -c pyproject.toml`, `pytest` 를
  실행합니다.
- **`release.yml`** 은 `main` 에서 `ci.yml` 이 완료되기를
  기다립니다(`workflow_run` 트리거). CI 가 성공한 경우에만
  실행됩니다. **`main` 으로의 모든 CI 성공 푸시는 릴리스입니다** —
  워크플로가 `pyproject.toml` 의 패치 버전을 자동으로 올리고, 그
  올림을 `chore: bump version to X.Y.Z` 로 `main` 에 되커밋하고,
  파이프라인을 실행합니다:
  1. **`bump-version`** — `pyproject.toml` 에서 현재 `X.Y.Z` 를 읽고,
     `X.Y.(Z+1)` 로 올리고, 워크플로 `GITHUB_TOKEN` 을 사용해 `main`
     으로 커밋 + 푸시. 그 푸시는 CI 를 다시 트리거하지 않으므로
     (`GITHUB_TOKEN` 이 구동한 푸시는 새 워크플로 실행을 시작할 수
     없다는 GitHub 규칙에 따라) 사이클이 자연히 종료됩니다.
  2. **`publish-pypi`** — sdist + wheel 빌드, `twine check`,
     `PYPI_API_TOKEN` 을 통한 `twine upload`.
  3. **`create-draft-release`** — 자동 생성된 노트와 함께 태그
     `v<version>` 에 *초안* GitHub 릴리스를 엽니다.
  4. **`build-nuitka`** — Windows 러너에서 Nuitka 독립 실행형 번들을
     컴파일(진입점: `--python-flag=-m` 를 통한 `python -m
     thesisagents`), 스모크 테스트, 결과 `thesisagents.dist/` 폴더를
     zip 으로 압축하고, zip + `.sha256` 체크섬을 초안 릴리스에 첨부.
     설계상 독립 실행형(onefile 아님): onefile 은 매 실행마다
     `%TEMP%` 로 자기 압축을 풀어 시작 지연을 더하고 잠긴 머신에서
     안티바이러스 휴리스틱을 건드립니다. 마찬가지로 설계상
     Windows 전용: Linux / macOS 사용자는 PyPI 에서 설치합니다.
     `pyproject.toml` 에 키를 둔 빌드 캐시가 웜 빌드를 콜드 ~85분
     에서 ~5–10분으로 줄입니다.
  5. **`publish-release`** — Nuitka 자산이 업로드되면 초안 표시를
     해제하여 사용자가 절반만 완성된 릴리스를 결코 보지 않게 합니다.

  **릴리스 건너뛰기.** 커밋 메시지 어디에든 `[skip release]` 를
  포함하면 올림 + 모든 다운스트림 잡이 건너뛰어집니다 — 버전 번호를
  소모해선 안 되는 문서 전용 / 오타 / 리팩터 커밋에 사용하세요.

PyPI 게시 + 릴리스 실행 파일을 활성화하려면:

1. <https://pypi.org/manage/account/token/> 에서 프로젝트 범위 API
   토큰을 생성합니다.
2. GitHub 저장소에서: `Settings → Secrets and variables → Actions →
   New repository secret`. 이름을 `PYPI_API_TOKEN` 으로 하고 토큰
   값을 붙여넣습니다.
3. GitHub Actions 가 `main` 에 푸시하도록 허용: `Settings → Actions →
   General → Workflow permissions → Read and write permissions`. 올림
   커밋은 워크플로의 `GITHUB_TOKEN` 이 푸시합니다.
4. PR 을 `main` 에 병합하여 릴리스를 냅니다. 파이프라인은 PyPI 게시에
   ~3–5분, Windows zip 첨부에 추가로 ~80–90분(콜드) 또는 ~5–10분
   (웜 Nuitka 캐시)이 걸립니다.

`publish-pypi` 잡은 의도적으로 GitHub Environment 를 붙이지
않으므로, 각 실행이 저장소 홈의 "Deployment" 사이드바 위젯이 아니라
(Nuitka `.exe` 가 첨부된) 릴리스 항목으로 표출됩니다 — 릴리스는
자신만의 전용 페이지를 갖고, 그 위의 Deployment 항목은 그저
불필요한 잡음일 뿐입니다.

## 라이선스

`LICENSE` 를 참고하세요. arXiv API 는 arXiv 의 API 이용 약관
(<https://info.arxiv.org/help/api/tou.html>)에 따라 사용됩니다 — 3초당
1요청의 소프트 리밋을 준수하세요; 번들된 페처가 토큰 버킷을 통해
이미 이를 강제합니다.

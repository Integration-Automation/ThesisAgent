ThesisAgents 사용자 가이드
============================

키워드 기반 논문 검색 어시스턴트. arXiv, Semantic Scholar, OpenAlex,
PubMed, ACM, IEEE Xplore, DBLP, Crossref, OpenAIRE, Springer Nature, Europe PMC, DOAJ, HAL, CORE,
Google Scholar 에서 결과를 가져와 논문 발표용 PowerPoint 슬라이드, Excel
워크북, BibTeX 파일로 내보냅니다. CLI 호출 한 번 또는 MCP 도구 호출 한
번으로 모두 끝납니다.

.. contents:: 목차
   :depth: 2
   :local:

----

본 프로젝트를 구동하는 AI 에이전트에게
---------------------------------------

**당신이 LLM (Claude Code, Cursor, Aider, Codex CLI, …) 으로 무엇을 해야
할지 파악하기 위해 이 문서를 읽고 있다면 — 여기서 시작하세요.** 같은
규칙이 repo 루트의 ``AGENTS.md`` (에이전트 간 미러) 와 ``CLAUDE.md``
(정식 참조) 에도 고정되어 있습니다. 사소하지 않은 변경 전에 반드시 그쪽을
먼저 읽으세요.

**기본 산출물은 논문 한 편당 논문 발표급 리치 ``.pptx``** 이며, CLI 가
기본으로 내놓는 초록만 있는 라이트 덱이 아닙니다. 라이트 출력은 중간
산출물 — 그것을 업그레이드하는 것이 당신의 일입니다.

의사결정 트리
^^^^^^^^^^^^^

1. ``ANTHROPIC_API_KEY`` 설정됨? → CLI 만 실행. Anthropic API 경유 자동
   enrich.
2. 키 없음, LLM 이 구동 → **리치 요약을 직접 작성**\ . 각 PDF 읽기,
   rich-tier 필드로 ``PaperSummary`` 손으로 작성, ``scripts/regen_<query>.py``
   배치, 실행. **사용자에게 API 키 설정 요구 금지** — 당신이 LLM 입니다.
3. LLM 없음 (CI / cron) → 라이트 허용.

MCP 6 단계 워크플로
^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   1. (선택) list_sources()
   2. search(keywords, sources, top_tier_only=true, ...)
   3. (선택) download_pdfs(papers, out_dir="./exports/...")
   4. fetch_pdf_text(pdf_url=paper.pdf_url)           # 논문별
   5. (각 PDF 읽고 구조화된 summary dict 생성)
   6. export(papers=[{...paper, "summary": {...}}], language="ko", ...)

12 개 MCP 도구의 완전한 참조: :doc:`/mcp`.

필수: 인도 전 URL / DOI 검증
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

출판사 URL 경로는 **추측할 수 없습니다** — AAAI 는 숫자 ID
(``v40i5.37389``), IEEE 는 불투명 ``arnumber``, ACM 은 불투명 DOI 사용.
``Paper`` 를 손으로 작성할 때 ``url`` / ``doi`` / ``arxiv_id`` 는 **이
검색이 생성한 xlsx 에서 글자 그대로 복사**\ . 기억에서 쓰거나 제목으로
구성 금지.

xlsx 는 ``exports/<run>/<slug>-<timestamp>.xlsx`` 에 작성되며 열 7 = DOI,
열 8 = URL 입니다. regen 종료 후 다음 감사 실행:

.. code-block:: python

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

금지
^^^^

* 사용자에게 "``ANTHROPIC_API_KEY`` 설정하세요" 말하지 말 것 — 당신이 LLM.
* 라이트 ``.pptx`` 를 산출물로 취급 금지.
* ``download_pdfs`` 끝나도 멈추지 말 것.
* 논문에 없는 숫자, RQ, 기여, 한계 지어내기 금지.
* URL / DOI / arXiv ID 조작 금지.
* 실행 디렉토리에 무관한 다운로드 남기지 말 것. 키워드 검색은 주제와
  무관한 논문을 가져올 수 있습니다 ("Claude code" 쿼리가 Viterbi
  디코더 논문을 가져옴). 무관한 ``pdfs/<key>.pdf`` 와 경량
  ``<key>.pptx`` 를 삭제하고, 집계된 xlsx / bib 는 정직한 기록으로
  유지하세요. 전체 절차는 ``CLAUDE.md`` 의 "Pruning irrelevant
  downloads" 참조.
* "Claude", "Claude Code", "AI-generated", "GPT", "Copilot" 등
  AI 도구/모델 이름을 커밋, PR, 코드 주석, 문서에 언급 금지.

예제: ``scripts/regen_llm_security_batch.py`` (en, 8 편) 와
``scripts/regen_llm_security_batch_zh_tw.py`` (zh-tw).

----

설치
----

Python **3.12+** 필요.

.. code-block:: bash

   git clone <repo-url>
   cd ThesisAgents
   python -m venv .venv
   .venv\Scripts\Activate.ps1            # Windows PowerShell
   # source .venv/bin/activate           # Linux / macOS
   pip install -e .[dev]

선택 extras: ``[mcp]``, ``[intelligence]``, ``[web]``, ``[dev]``.

----

빠른 시작
---------

.. code-block:: bash

   # arXiv 검색 → 덱 + 워크북 + BibTeX
   thesisagents --query "diffusion models" --source arxiv --max 10 \
                  --out ./exports/

   # URL 로 단일 논문 → 덱 + BibTeX
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --filename-stem attention --out ./exports/

   # 덱을 한국어로 렌더링
   thesisagents --paper 1706.03762 --lang ko --out ./exports/

   # Python 파이프라인 enrichment (Anthropic 키 필요)
   export ANTHROPIC_API_KEY=sk-ant-...
   thesisagents --paper "https://arxiv.org/abs/1706.03762" \
                  --enrich --lang ko --out ./exports/

CLI 플래그 전체 표: :doc:`/cli`.

----

더 자세히
---------

* CLI 플래그 + 환경 변수: :doc:`/cli`
* 12 개 MCP 서버 도구: :doc:`/mcp`
* PPTX 편집 툴킷: :doc:`/pptx_editing`
* repo 루트의 ``readmes/README.ko.md`` 에 기능 전체 목록이 있습니다.
* 깊이 있는 기술 참조 (플러그인 아키텍처, 보안 정책, Definition of
  Done, SonarQube 규칙 등) 는 영어 가이드에 집중되어 있습니다:
  :doc:`/en/index`.

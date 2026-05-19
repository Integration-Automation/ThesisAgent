# AutoPaperToPPT

[![CI](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![Python](https://img.shields.io/pypi/pyversions/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/AutoPaperToPPT.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/autopapertoppt/badge/?version=latest)](https://autopapertoppt.readthedocs.io/en/latest/)

> **言語**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · **日本語** · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · [हिन्दी](README.hi.md) · [Bahasa Indonesia](README.id.md)
> **ドキュメント**: [autopapertoppt.readthedocs.io](https://autopapertoppt.readthedocs.io/en/latest/)

キーワード駆動の論文検索アシスタント。arXiv、Semantic Scholar、OpenAlex、PubMed、ACM(Crossref 経由)、IEEE Xplore、DBLP、汎用 Crossref、OpenAIRE、Springer Nature、Google Scholar から論文を取得し、統一されたレコード形式に正規化、重複排除後の結果集合を **論文発表用 PowerPoint スライド**、**Excel ワークブック**、**BibTeX ファイル** として出力します — CLI 1 回または MCP ツール呼び出し 1 回で完結。各論文の PDF を読んで構造化サマリを生成することも可能で、LLM-as-agent パスまたは Anthropic API パスから選べます。

## このプロジェクトを駆動する AI エージェントへ

**あなたが LLM(Claude Code、Cursor、Aider、Codex CLI、…)で、この README を読んで何をすべきか把握しようとしているなら、ここから始めてください。** 同じルールが [`AGENTS.md`](AGENTS.md)(エージェント横断のミラー)と [`CLAUDE.md`](CLAUDE.md)(正式な参照先)にも固定されています。非自明な変更を加える前にそちらを読んでください。

### ユーザーが本当に欲しいもの

デフォルトの納品物は **論文発表向けのリッチな `.pptx` を 1 論文 1 枚** であり、CLI がデフォルトで吐く要約だけの軽量デッキではありません。軽量版は中間成果物 — あなたの仕事はそれをアップグレードすることです。

### 判断フローチャート

1. 環境変数に `ANTHROPIC_API_KEY` が設定されているか? → CLI を実行するだけ。Anthropic API 経由で自動エンリッチされます。完了。
2. キーは無いが、あなた(LLM)がセッションを駆動している → **リッチサマリは自分で書く**。各 PDF を読み、`PaperSummary` をリッチ層のフィールド(`pain_points`、`research_question`、`contributions_detailed`、`headline_metrics`、`technique_table`、`method_sections`、`evaluation_sections`、`system_flow`、`research_questions`、`rq_results`、`core_observation`、`limitations`、`future_work`)で手書きし、`scripts/regen_<query>.py` を置いて実行。**ユーザーに API キーを設定するよう求めてはいけません** — あなたがその LLM です。
3. LLM 不在(CI / cron / 無人運転)→ 軽量版で OK。

### MCP 6 ステップワークフロー

```
1. (任意) list_sources()                                  # 有効なプラグインを確認
2. search(keywords, sources, top_tier_only=true, ...)
3. (任意) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # 論文ごと
5. (各 PDF を読み、構造化サマリ dict を生成)
6. export(papers=[{...paper, "summary": {...}}], language="ja", ...)
```

11 個の MCP ツール(`list_sources`、`download_pdfs`、`pptx_inspect` / `pptx_update_slide` / `pptx_add_slide` 等)の完全な参照は [`docs/mcp.md`](docs/mcp.md) にあります。

### 必須: 納品前に URL / DOI を検証

出版社の URL パスは **推測できません** — AAAI は数値 ID(`v40i5.37389`)、IEEE は不透明な `arnumber`、ACM は不透明な DOI を使います。`Paper` を手書きする際は、`url` / `doi` / `arxiv_id` を **検索で生成された xlsx から逐語コピー** してください — 記憶やタイトルからの構築は禁止。

xlsx は `exports/<run>/<slug>-<timestamp>.xlsx` に出力され、列 7 = DOI、列 8 = URL。regen スクリプト実行後にこの監査を実行:

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

過去に本番で検出された 2 件の偽造: AAAI 巻号の誤り(`v39i23.34521` 対 実際の `v39i22.34537`)、著者 slug パスの捏造(`view/fang2026` 代わりに `v40i5.37389`)。

### 実例

[`scripts/regen_llm_security_batch.py`](scripts/regen_llm_security_batch.py) にこの流れで手書きされた 8 篇のリッチサマリが収録されています。複数論文検索のテンプレートとして使ってください。zh-tw コンパニオンは [`scripts/regen_llm_security_batch_zh_tw.py`](scripts/regen_llm_security_batch_zh_tw.py)。

### 禁止事項

- **やってはいけない**: 複数論文検索の最後に「`ANTHROPIC_API_KEY` を設定すればリッチデッキが出る」とユーザーに伝える — あなたがそのサマリを書ける LLM です。
- **やってはいけない**: 各論文の軽量 `.pptx` を最終納品物として扱う。
- **やってはいけない**: `download_pdfs` が「N 件保存」と報告した時点で止める — それはリッチ作成フェーズの開始であって終わりではない。
- **やってはいけない**: 論文に書かれていない数字、RQ、貢献、限界を捏造する。
- **やってはいけない**: URL / DOI / arXiv ID を捏造する — 上記ルール参照。
- **やってはいけない**: 実行ディレクトリに無関係なダウンロードを残す。キーワード検索は関連性ベースなので、「Claude code」検索で Viterbi デコーダ論文がヒットしたり、「LLM code review」検索で物体検出のレビュー論文がヒットしたりする。無関係と判断した論文の `pdfs/<key>.pdf` と軽量 `<key>.pptx` を削除すること。集約 xlsx / bib は検索の正直な記録として残す。
- **やってはいけない**: コミットメッセージ、PR 説明、コードコメント、ドキュメントで「Claude」「Claude Code」「AI-generated」「GPT」「Copilot」など AI ツール / モデル名に言及する。

## 機能

- **11 個のプラガブルソース**: `arxiv`、`semantic_scholar`、`openalex`、`pubmed`、`acm`(Crossref スコープ)、`dblp`、`crossref`(汎用)、`openaire`、`springer`(API キー必須)、`ieee`(API キーまたはスクレイピングオプトイン)、`scholar`(スクレイピングオプトイン)。各々が `sources/<name>/` 配下で `Fetcher` アダプタとして実装されています。デフォルトでは旗艦級 CS 学会誌 + Nature/Science/PNAS をホワイトリストし、`--all-venues` で無効化可能。
- **単一論文モード**: arXiv ID、arXiv URL、DOI、PMID、または IEEE 文書 URL を貼り付けると、AutoPaperToPPT が対応するソース経由でそれを解決し、同じエクスポートバンドルを生成します。論文読書ノート・修論発表準備に最適。
- **ローカル PDF モード** (`--pdf <path>`): PDF 1 つまたはディレクトリを渡す。ヒューリスティック抽出器が各 PDF の先頭から **タイトル、著者、年度、arXiv ID、DOI、本物の要約** を引き出し(明示的な `Abstract` / `ABSTRACT` / `摘要` ヘッダーを基準とし、適当な前置切りではない)。単一 PDF では `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` で上書き可能。ディレクトリでは各ファイル独自の抽出結果が優先され、各論文は自身の BibTeX キー名でデッキを生成。
- **5 つのエクスポータ**:
  - `.pptx` — 16:9 ワイドスクリーン、ページ番号付き、3 つのレンダリング層(軽量要約のみ / フラット強化 / **論文発表級** にはペインポイント四象限、KPI コールアウト、技術比較表、RQ ごとの結果表、貢献まとめ、コア観察、限界 & 今後の課題、Q&A、参考文献)。すべてのテンプレート文字列は **14 言語** に i18n 対応: English、繁體中文、简体中文、日本語、Español、Français、Deutsch、한국어、Português、Русский、Italiano、Tiếng Việt、हिन्दी、Bahasa Indonesia。
  - `.xlsx` — Papers シート + Query 出典シート、URL / PDF ハイパーリンク、ヘッダー固定、列幅自動調整。列 5(**Source**)は実際の出版場所(例「IEEE Access」)、列 6(**Indexed via**)はメタデータを返したフェッチャ(例「openalex」)を表示し、2 つの情報が混同されないようになっています。
  - `.md` — 完全なソース / タイトル / 要約リスト。
  - `.bib` — 衝突しない引用キー、LaTeX エスケープ済みフィールド。
  - `.json` — 下流ツーリング用の生ペイロード。
- **PPT 編集ツールキット**: `autopapertoppt.exporters.pptx_edit`(inspect / update_slide / delete_slide / reorder_slides / add_slide)はエクスポータが生成した任意のデッキに対して動作。LLM エージェントが生成済みデッキで反復できる `pptx_*` MCP ツールも同梱。
- **MCP サーバー**: 11 ツール — `list_sources`(発見)、`search`、`fetch_paper`、`fetch_pdf_text`、`download_pdfs`、`export`、および 5 個の `pptx_*` 編集ツール。MCP 対応 LLM(Claude Code、Claude Desktop、Cursor、…)から全ワークフローを駆動可能。
- **2 つのエンリッチパス**(要約だけでなく本物の論文発表級デッキへ):
  - **LLM-as-agent(API キー不要)** — 呼び出し側 LLM が `fetch_pdf_text` で本文を読み、構造化サマリをコンテキスト内で書き、`export` に渡す。
  - **Python パイプライン (`--enrich`)** — CLI が Anthropic API を直接呼ぶ。デフォルトモデルは `claude-opus-4-7`。
- **デフォルトで安全**: HTTPS-only HTTP トランスポート、ソースごとのレート制限(トークンバケット)、任意の XML ペイロードには `defusedxml`、パストラバーサル対策済みエクスポートパス、ユーザー入力に `eval` / `exec` / `pickle` を使わない。Scholar・IEEE スクレイピングはデフォルト無効(env var オプトイン)。

## クイックスタート

```powershell
git clone <repo-url>
cd AutoPaperToPPT
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# dev extras 込みでインストール(MCP SDK と intelligence 依存も含む)
pip install -e .[dev]
```

arXiv 検索 → デッキ + ワークブック + BibTeX を出力(`--query` のデフォルト):

```powershell
py -m autopapertoppt --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

URL で単一論文を取得 — デフォルトは `.pptx + .bib`(1 行の `.xlsx` は意味が薄い):

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

デッキを日本語で生成:

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --lang ja --out .\exports\
```

LLM パイプラインによるエンリッチ(Python が直接 Anthropic を呼ぶ — API キー必須):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang ja --out .\exports\
```

## CLI フラグ

| フラグ | 用途 |
|---|---|
| `--query` / `-q` | キーワード(`--paper` が無い場合は必須)。 |
| `--paper` / `-p` | arXiv ID / URL、DOI、PMID、または IEEE 文書 URL。`--query` と排他。 |
| `--source` / `-s` | カンマ区切りのソースリスト。デフォルト `arxiv`。 |
| `--max` / `-n` | ソースごとの最大件数(1..200)。デフォルト 25。 |
| `--year-from` / `--year-to` | 年度フィルタ(両端含む)。 |
| `--export` / `-e` | 形式: `pptx,xlsx,md,bib,json` の任意組合せ。デフォルトはモードによる(下記参照)。 |
| `--out` / `-o` | 出力ディレクトリ。デフォルト `./exports`。 |
| `--filename-stem` | 自動生成ファイル名の stem を上書き。 |
| `--no-abstract` | エクスポートから要約内容を除外。 |
| `--lang` / `-l` | デッキ言語: 14 種から — `en`、`zh-tw`、`zh-cn`、`ja`、`es`、`fr`、`de`、`ko`、`pt`、`ru`、`it`、`vi`、`hi`、`id`。デフォルト `en`。 |
| `--enrich` | PDF を DL → Anthropic 要約。`ANTHROPIC_API_KEY` と `[intelligence]` extra が必要。 |
| `--lightweight` | `ANTHROPIC_API_KEY` 設定済みでも軽量デッキを強制。 |
| `--llm-model` | エンリッチのデフォルト `claude-opus-4-7` を上書き。 |
| `--all-venues` | トップティアホワイトリストを無効化(デフォルトは旗艦級 CS 学会誌 + Nature / Science / PNAS / CACM / LNCS のみ)。 |
| `--paywall-threshold` | 確認プロンプトをトリガする paywall 結果の割合。デフォルト 0.30。 |
| `--yes` | paywall プロンプトをスキップ。 |
| `--max-slides` | 論文ごとのスライド上限(デフォルト 25、0 は無制限)。 |
| `--quiet` | 論文ごとの出力を抑制。 |

### 環境変数

| 変数 | 利用箇所 | 用途 |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | LLM 認証。MCP の LLM-as-agent パスでは不要。 |
| `AUTOPAPERTOPPT_LLM_MODEL` | `--enrich` | デフォルト `claude-opus-4-7` を上書き。 |
| `AUTOPAPERTOPPT_S2_API_KEY` | Semantic Scholar | 高いレート上限。任意。 |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | PubMed | NCBI の匿名上限(3/s)を 10/s に引き上げ。任意。 |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | PubMed、ACM、Crossref、OpenAlex | リクエストを Crossref の polite プールに入れる。 |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | IEEE(API パス) | 公式 IEEE Xplore API、対象論文の `pdf_url` を公開。 |
| `AUTOPAPERTOPPT_DISABLE_IEEE_SCRAPING` | IEEE(スクレイピングパス) | `=1` でスクレイピング有効。API キー設定時は不要。 |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | ACM、Crossref | Crossref Plus 加入者トークン(Bearer ヘッダ)。任意。 |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | Springer | 必須。<https://dev.springernature.com/> から無料キー。未設定だとプラグインは沈黙してスキップされる。 |
| `AUTOPAPERTOPPT_CHROME_PROFILE_DIR` | Scholar + IEEE + paywalled-PDF downloads | Persistent Chrome `--user-data-dir`. Set this and complete VPN / SSO once; subsequent runs inherit the cookies. |
| `AUTOPAPERTOPPT_DISABLE_WEBRUNNER` | Scholar + IEEE + paywalled-PDF downloads | `=1` forces the httpx paths instead of driving real Chrome. For CI / Docker without a Chrome binary. |
| `AUTOPAPERTOPPT_CORE_API_KEY` | OA resolver | Free key from <https://core.ac.uk/services/api>. Enables the CORE.ac.uk lookup step in the OA PDF resolver. |
| `AUTOPAPERTOPPT_DISABLE_SCHOLAR_SCRAPING` | Google Scholar | `=1` でスクレイピング有効。デフォルト無効 — Scholar ToS がスクレイピングを禁止。 |
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | PDF ダウンローダ | Netscape 形式 `cookies.txt`。デフォルト無効。所属機関アクセス権を持つ出版社にのみ使用してください。 |
| `AUTOPAPERTOPPT_LOG_LEVEL` | logger | デフォルト `INFO`、詳細ログは `DEBUG`。 |

デフォルト: `--query` → `pptx,xlsx,bib`、`--paper` → `pptx,bib`。常に明示的な `--export` で上書き可能。

## MCP サーバー

Claude Code に登録:

```powershell
claude mcp add autopapertoppt -- ".venv\Scripts\python.exe" -m autopapertoppt.mcp
```

または settings ファイルを編集:

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

ツール:

| ツール | 用途 |
|---|---|
| `list_sources` | プラグインを列挙し、現在の env で各々が有効かを報告。`search` 前に 1 回呼ぶ。 |
| `search` | キーワード → 論文リスト。`top_tier_only`、`min_citations` を受理。`sources` 省略時は API キー不要のソース全体。 |
| `fetch_paper` | arXiv / DOI / PMID / IEEE 識別子 → 単一論文。 |
| `fetch_pdf_text` | 単一 PDF をダウンロード、抽出した本文を返す。**MCP 経由で「論文を読んだ」状態に至る入口。** |
| `download_pdfs` | 論文リストの PDF を `{out_dir}/pdfs/` に一括ダウンロード。BibTeX キーをキーとする論文ごとの結果を返す。 |
| `export` | 論文リスト + 形式 → `.pptx/.xlsx/.md/.bib/.json` を書き出し。リッチ thesis-style スキーマの `summary` フィールドと、`max_slides_per_paper`(デフォルト 25)を受理。 |
| `pptx_inspect` | 既存デッキのスライド / シェイプ構造を読む。 |
| `pptx_update_slide` | `title` / `body` / `meta`(シェイプ名経由)または任意のシェイプ(インデックス経由)を置換。 |
| `pptx_delete_slide` | スライドとその part relationship を削除。 |
| `pptx_reorder_slides` | `sldIdLst` 経由でスライド順序を入れ替え。 |
| `pptx_add_slide` | 末尾追加または指定 position に新規 title / body / meta スライドを挿入。 |

LLM-as-agent フロー(`ANTHROPIC_API_KEY` 不要 — LLM 自身がエージェント):

```
1. (任意) list_sources()                           # 有効なプラグインを発見
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (任意) download_pdfs(papers, out_dir="./exports/...")  # PDF を永続化
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # 論文ごと
5. (LLM が本文を読み、構造化 `summary` dict を生成)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="ja", formats=["pptx","bib"], ...)
```

完全な参照は [`docs/mcp.md`](docs/mcp.md)。

## プロジェクト構成

```
AutoPaperToPPT/
├── autopapertoppt/                 # メインパッケージ
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # HTTPS-only async クライアント、トークンバケットレート制限
│   ├── exporters/                   # pptx (thesis-style) · xlsx · bib · md · json · pptx_edit · i18n
│   ├── intelligence/                # PDF 取得 + Anthropic 要約([intelligence] extra)
│   ├── mcp/                         # FastMCP サーバー(11 ツール)
│   ├── utils/                       # logging、path safety
│   ├── cli.py                       # argparse CLI
│   └── __main__.py
├── sources/                         # プラグインフォルダ: arxiv, semantic_scholar,
│                                    #   openalex, pubmed, acm, ieee, scholar,
│                                    #   dblp, crossref, openaire, springer
├── tests/                           # pytest スイート + 記録済み fixture(ライブ HTTP 不可)
├── docs/                            # Sphinx(14 言語ツリー)
├── scripts/                         # 一回限りの regen スクリプト
└── pyproject.toml                   # ruff、bandit、build、optional extras
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r autopapertoppt/ sources/
```

bandit の `-c` フラグは必須 — 無いと bandit はプロジェクトの skip 設定を無視します。pptx エクスポータを触る場合は overflow チェックも実行(`CLAUDE.md`「Slide Deck Rules」参照)。

## ライセンス

`LICENSE` 参照。arXiv API は arXiv の利用規約(<https://info.arxiv.org/help/api/tou.html>)に従って使用 — 3 秒あたり 1 リクエストのソフト上限を遵守。同梱フェッチャは token bucket でこのレートを既に強制しています。

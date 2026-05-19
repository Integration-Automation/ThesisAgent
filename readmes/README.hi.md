# AutoPaperToPPT

[![CI](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml/badge.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/ci.yml)
[![Release](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/Integration-Automation/AutoPaperToPPT/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![Python](https://img.shields.io/pypi/pyversions/autopapertoppt.svg)](https://pypi.org/project/autopapertoppt/)
[![License: MIT](https://img.shields.io/github/license/Integration-Automation/AutoPaperToPPT.svg)](https://github.com/Integration-Automation/AutoPaperToPPT/blob/main/LICENSE)
[![Docs](https://readthedocs.org/projects/autopapertoppt/badge/?version=latest)](https://autopapertoppt.readthedocs.io/en/latest/)

> **भाषाएँ**: [English](../README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [한국어](README.ko.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Italiano](README.it.md) · [Tiếng Việt](README.vi.md) · **हिन्दी** · [Bahasa Indonesia](README.id.md)
> **दस्तावेज़ीकरण**: [autopapertoppt.readthedocs.io](https://autopapertoppt.readthedocs.io/en/latest/)

कीवर्ड-संचालित शोध-पत्र खोज सहायक। arXiv, Semantic Scholar, OpenAlex, PubMed, ACM (Crossref के माध्यम से), IEEE Xplore, DBLP, सामान्य Crossref, OpenAIRE, Springer Nature और Google Scholar से परिणाम लाता है; उन्हें एकल रिकॉर्ड प्रारूप में सामान्यीकृत करता है; और डुप्लीकेट-मुक्त समूह को **थीसिस-शैली PowerPoint स्लाइड**, **Excel वर्कबुक** और **BibTeX फ़ाइल** के रूप में निर्यात करता है — एक CLI कॉल या एक MCP टूल कॉल से सब कुछ। वैकल्पिक रूप से प्रत्येक शोध-पत्र को उसकी PDF पढ़कर समृद्ध कर सकता है, या तो संदर्भ में (LLM-as-agent पथ) या Anthropic API के माध्यम से (Python pipeline पथ)।

## इस परियोजना को चलाने वाले AI एजेंट के लिए

**यदि आप एक LLM (Claude Code, Cursor, Aider, Codex CLI, …) हैं जो यह जानने के लिए इस README को पढ़ रहे हैं कि क्या करना है — यहाँ से शुरू करें।** वही नियम [`AGENTS.md`](AGENTS.md) (एजेंट-क्रॉस मिरर) और [`CLAUDE.md`](CLAUDE.md) (आधिकारिक संदर्भ) में भी फिक्स हैं; गैर-तुच्छ परिवर्तनों से पहले उन्हें पढ़ें।

### उपयोगकर्ता वास्तव में क्या चाहता है

डिफ़ॉल्ट डिलीवरेबल है **हर शोध-पत्र के लिए एक थीसिस-शैली समृद्ध `.pptx`**, न कि हल्का सार-केवल डेक जो CLI डिफ़ॉल्ट रूप से उत्पन्न करता है। हल्का आउटपुट एक मध्यवर्ती कलाकृति है — आपका काम उसे उन्नत करना है।

### निर्णय वृक्ष

1. क्या परिवेश में `ANTHROPIC_API_KEY` सेट है? → बस CLI चलाएँ; यह Anthropic API के माध्यम से स्वचालित रूप से समृद्ध हो जाता है। हो गया।
2. कुंजी नहीं, लेकिन आप (LLM) सत्र चला रहे हैं → **समृद्ध सारांश आप स्वयं तैयार करें**। प्रत्येक PDF पढ़ें, हाथ से rich-tier फ़ील्ड्स (`pain_points`, `research_question`, `contributions_detailed`, `headline_metrics`, `technique_table`, `method_sections`, `evaluation_sections`, `system_flow`, `research_questions`, `rq_results`, `core_observation`, `limitations`, `future_work`) वाला `PaperSummary` लिखें, एक `scripts/regen_<query>.py` रखें और उसे चलाएँ। **उपयोगकर्ता से API key सेट करने को न कहें** — आप ही वह LLM हैं जो सारांश लिख सकता था।
3. लूप में LLM नहीं (CI / cron / अनदेखा) → हल्का आउटपुट स्वीकार्य।

### MCP 6-चरण कार्यप्रवाह

```
1. (वैकल्पिक) list_sources()                              # कौन से plugin सक्षम हैं
2. search(keywords, sources, top_tier_only=true, ...)
3. (वैकल्पिक) download_pdfs(papers, out_dir="./exports/...")
4. fetch_pdf_text(pdf_url=paper.pdf_url)                  # प्रति शोध-पत्र
5. (आप प्रत्येक PDF पढ़ें और संरचित सारांश dict तैयार करें)
6. export(papers=[{...paper, "summary": {...}}], language="hi", ...)
```

ग्यारह MCP उपकरण (`list_sources`, `download_pdfs`, `pptx_inspect` / `pptx_update_slide` / `pptx_add_slide` आदि सहित) [`docs/mcp.md`](docs/mcp.md) में प्रलेखित हैं।

### अनिवार्य: डिलीवरी से पहले URL / DOI सत्यापन

प्रकाशक URL पथ **अनुमान योग्य नहीं हैं** — AAAI संख्यात्मक ID (`v40i5.37389`) उपयोग करता है, IEEE अपारदर्शी `arnumber`, ACM अपारदर्शी DOI। जब आप हाथ से `Paper` लिखते हैं, **`url` / `doi` / `arxiv_id` को इस खोज द्वारा उत्पन्न xlsx से शब्दशः कॉपी करें** — कभी स्मृति से नहीं, कभी शीर्षक से निर्मित नहीं।

xlsx `exports/<run>/<slug>-<timestamp>.xlsx` में लिखी जाती है, कॉलम 7 = DOI, कॉलम 8 = URL। regen स्क्रिप्ट समाप्त होने पर ऑडिट करें:

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

प्रोडक्शन में इसी से पकड़े गए दो कूट: गलत AAAI खंड (`v39i23.34521` बनाम वास्तविक `v39i22.34537`) और मनगढ़ंत लेखक-स्लग पथ (`view/fang2026` के बजाय `v40i5.37389`)।

### कार्यान्वित उदाहरण

[`scripts/regen_llm_security_batch.py`](scripts/regen_llm_security_batch.py) में इस प्रक्रिया के अनुसार हाथ से लिखे 8 समृद्ध सारांश हैं। किसी भी बहु-शोध-पत्र खोज के लिए टेम्पलेट के रूप में उपयोग करें। zh-tw समकक्ष [`scripts/regen_llm_security_batch_zh_tw.py`](scripts/regen_llm_security_batch_zh_tw.py) में।

### निषेध

- **न** बहु-शोध-पत्र खोज को यह कहकर समाप्त करें कि "समृद्ध डेक के लिए `ANTHROPIC_API_KEY` सेट करें" — आप ही वह LLM हैं जो सारांश लिख सकता था।
- **न** प्रति-शोध-पत्र हल्के `.pptx` को डिलीवरेबल मानें।
- **न** जब `download_pdfs` "N PDF सहेजे" रिपोर्ट करे तब रुकें — यह समृद्ध-लेखन चरण का आरंभ है, अंत नहीं।
- **न** शोध-पत्र में अनुपस्थित संख्याएँ, RQ, योगदान या सीमाएँ गढ़ें।
- **न** URLs / DOIs / arXiv IDs मनगढ़ंत करें — ऊपर नियम देखें।
- **न** run निर्देशिका में अप्रासंगिक डाउनलोड छोड़ें। कीवर्ड खोज में कभी-कभी विषय से बाहर के पेपर शामिल हो जाते हैं ("Claude code" क्वेरी ने एक Viterbi डिकोडर पेपर खींच लिया; "LLM code review" ने एक object detection साहित्य समीक्षा खींच ली)। विषय से बाहर के रूप में वर्गीकृत करने के बाद, उनके `pdfs/<key>.pdf` और हल्के `<key>.pptx` को हटा दें; aggregate xlsx / bib को खोज ने क्या लौटाया इसके ईमानदार रिकॉर्ड के रूप में रखें।
- **न** commit संदेश, PR विवरण, कोड टिप्पणी या प्रलेखन में "Claude", "Claude Code", "AI-generated", "GPT", "Copilot" या किसी AI टूल/मॉडल नाम का उल्लेख करें।

## विशेषताएँ

- **ग्यारह प्लग-इन योग्य स्रोत**: `arxiv`, `semantic_scholar`, `openalex`, `pubmed`, `acm` (Crossref के माध्यम से ACM तक सीमित), `dblp`, `crossref` (सामान्य), `openaire`, `springer` (API key आवश्यक), `ieee` (API key या स्क्रैपिंग opt-in), `scholar` (स्क्रैपिंग opt-in)। प्रत्येक `sources/<name>/` के अंतर्गत एक `Fetcher` एडाप्टर के पीछे रहता है। शीर्ष-स्तर वेन्यू श्वेतसूची डिफ़ॉल्ट रूप से परिणामों को प्रमुख CS सम्मेलनों/जर्नल + Nature/Science/PNAS तक फ़िल्टर करती है; `--all-venues` से अक्षम।
- **एकल-शोध-पत्र मोड**: arXiv ID, arXiv URL, DOI, PMID, या IEEE दस्तावेज़ URL चिपकाएँ — AutoPaperToPPT इसे सही स्रोत के माध्यम से हल करता है और वही निर्यात बंडल जारी करता है। पठन नोट्स और रक्षा तैयारी के लिए उपयोगी।
- **स्थानीय PDF मोड** (`--pdf <पथ>`): एक PDF या निर्देशिका पास करें। एक हेयूरिस्टिक एक्सट्रैक्टर प्रत्येक PDF के आरंभ से **शीर्षक, लेखक, वर्ष, arXiv ID, DOI और वास्तविक सार** निकालता है (स्पष्ट `Abstract` / `ABSTRACT` / `摘要` हेडर पर एंकर, अंधे उपसर्ग पर नहीं)। `--title` / `--authors` / `--year` / `--venue` / `--doi` / `--arxiv-id` एकल-PDF कॉल पर ओवरराइड करते हैं; निर्देशिका मोड में, प्रति-फ़ाइल निष्कर्षण जीतता है — प्रत्येक शोध-पत्र अपनी BibTeX कुंजी के नाम पर अपना डेक प्राप्त करता है।
- **पाँच एक्सपोर्टर**:
  - `.pptx` — 16:9 वाइडस्क्रीन, पृष्ठ-संख्यित, तीन रेंडरिंग स्तर (हल्का केवल-सार · enriched-flat · **थीसिस-शैली** दर्द-बिंदु चतुष्कोण, KPI कॉलआउट, तकनीक-तुलना तालिकाएँ, प्रति-RQ परिणाम तालिकाएँ, योगदान सारांश, मूल अवलोकन, सीमाएँ & भविष्य कार्य, Q&A, संदर्भ)। सभी टेम्पलेट स्ट्रिंग्स **14 भाषाओं** में i18n: English, 繁體中文, 简体中文, 日本語, Español, Français, Deutsch, 한국어, Português, Русский, Italiano, Tiếng Việt, हिन्दी, Bahasa Indonesia।
  - `.xlsx` — Papers शीट + Query प्रोवेनेंस शीट, URL / PDF हाइपरलिंक, फ़्रोज़न हेडर, स्वचालित कॉलम चौड़ाई। कॉलम 5 (**Source**) वास्तविक प्रकाशन स्थान (जैसे "IEEE Access") दिखाता है; कॉलम 6 (**Indexed via**) दिखाता है कि किस fetcher ने मेटाडेटा लौटाया (जैसे "openalex"), ताकि दोनों जानकारियाँ कभी न उलझें।
  - `.md` — पूर्ण स्रोत / शीर्षक / सार सूची।
  - `.bib` — टकराव-मुक्त उद्धरण कुंजियाँ, LaTeX-एस्केप्ड फ़ील्ड्स।
  - `.json` — डाउनस्ट्रीम टूलिंग के लिए कच्चा payload।
- **PPT संपादन टूलकिट**: `autopapertoppt.exporters.pptx_edit` (inspect / update_slide / delete_slide / reorder_slides / add_slide) एक्सपोर्टर द्वारा उत्पन्न किसी भी डेक पर काम करता है, साथ ही समकक्ष `pptx_*` MCP उपकरण ताकि एक LLM एजेंट उत्पन्न डेक पर पुनरावृत्ति कर सके।
- **MCP सर्वर**: 11 उपकरण — `list_sources` (खोज), `search`, `fetch_paper`, `fetch_pdf_text`, `download_pdfs`, `export`, और पाँच `pptx_*` संपादन उपकरण। किसी भी MCP-अनुकूल LLM (Claude Code, Claude Desktop, Cursor, …) को पूरा कार्यप्रवाह संचालित करने देता है।
- **दो समृद्धि पथ** सार से आगे एक वास्तविक थीसिस-शैली डेक तक:
  - **LLM-as-agent (कोई API key नहीं)** — कॉलिंग LLM `fetch_pdf_text` के माध्यम से PDF टेक्स्ट पढ़ता है, संदर्भ में संरचित सारांश लिखता है, और `export` को पास करता है।
  - **Python pipeline (`--enrich`)** — CLI स्वयं Anthropic API कॉल करती है; डिफ़ॉल्ट मॉडल `claude-opus-4-7`।
- **डिफ़ॉल्ट रूप से सुरक्षित**: HTTPS-only HTTP परिवहन, प्रति-स्रोत दर सीमा (token bucket), किसी भी XML payload के लिए `defusedxml`, path-traversal-सुरक्षित निर्यात पथ, उपयोगकर्ता इनपुट पर `eval` / `exec` / `pickle` नहीं। Scholar और IEEE स्क्रैपिंग डिफ़ॉल्ट रूप से बंद (env-var opt-in)।

## त्वरित शुरुआत

```powershell
git clone <repo-url>
cd AutoPaperToPPT
python -m venv .venv
.venv\Scripts\Activate.ps1            # Windows PowerShell
# source .venv/bin/activate           # Linux / macOS

# dev extras के साथ इंस्टॉल (MCP SDK और intelligence deps भी आते हैं)
pip install -e .[dev]
```

arXiv खोजें और डेक + वर्कबुक + BibTeX निर्यात करें (`--query` के लिए डिफ़ॉल्ट):

```powershell
py -m autopapertoppt --query "diffusion models" --source arxiv --max 10 `
                      --out .\exports\
```

URL से एक शोध-पत्र लाएँ — डिफ़ॉल्ट `.pptx + .bib`:

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --filename-stem attention `
                      --out .\exports\
```

डेक हिंदी में रेंडर करें:

```powershell
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --lang hi --out .\exports\
```

LLM-pipeline समृद्धि (Python स्वयं Anthropic कॉल करता है — API key आवश्यक):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py -m autopapertoppt --paper "https://arxiv.org/abs/1706.03762" `
                      --enrich --lang hi --out .\exports\
```

## CLI फ़्लैग्स

| फ़्लैग | उद्देश्य |
|---|---|
| `--query` / `-q` | कीवर्ड (`--paper` न हो तो अनिवार्य)। |
| `--paper` / `-p` | arXiv ID/URL, DOI, PMID, या IEEE दस्तावेज़ URL। `--query` के साथ परस्पर अनन्य। |
| `--source` / `-s` | अल्पविराम-पृथक स्रोत सूची। डिफ़ॉल्ट `arxiv`। |
| `--max` / `-n` | प्रति स्रोत अधिकतम परिणाम (1..200)। डिफ़ॉल्ट 25। |
| `--year-from` / `--year-to` | समावेशी वर्ष फ़िल्टर। |
| `--export` / `-e` | प्रारूप: `pptx,xlsx,md,bib,json` में से कोई भी। डिफ़ॉल्ट मोड पर निर्भर (नीचे देखें)। |
| `--out` / `-o` | आउटपुट निर्देशिका। डिफ़ॉल्ट `./exports`। |
| `--filename-stem` | उत्पन्न फ़ाइल नाम stem ओवरराइड। |
| `--no-abstract` | निर्यात से सार सामग्री छोड़ें। |
| `--lang` / `-l` | डेक भाषा: 14 में से एक — `en`, `zh-tw`, `zh-cn`, `ja`, `es`, `fr`, `de`, `ko`, `pt`, `ru`, `it`, `vi`, `hi`, `id`। डिफ़ॉल्ट `en`। |
| `--enrich` | PDF डाउनलोड + Anthropic सारांश। `ANTHROPIC_API_KEY` और `[intelligence]` extra आवश्यक। |
| `--lightweight` | `ANTHROPIC_API_KEY` सेट होने पर भी हल्के डेक के लिए बाध्य करें। |
| `--llm-model` | डिफ़ॉल्ट `claude-opus-4-7` ओवरराइड। |
| `--all-venues` | शीर्ष-स्तर श्वेतसूची अक्षम (डिफ़ॉल्ट प्रमुख CS स्थल + Nature / Science / PNAS / CACM / LNCS रखता है)। |
| `--paywall-threshold` | paywall परिणामों का अनुपात जो पुष्टिकरण प्रॉम्प्ट ट्रिगर करता है। डिफ़ॉल्ट 0.30। |
| `--yes` | paywall प्रॉम्प्ट छोड़ें। |
| `--max-slides` | प्रति-शोध-पत्र स्लाइड सीमा (डिफ़ॉल्ट 25; 0 असीमित के लिए)। |
| `--quiet` | प्रति-शोध-पत्र प्रिंट दबाएँ। |

### पर्यावरण चर

| चर | उपयोग | उद्देश्य |
|---|---|---|
| `ANTHROPIC_API_KEY` | `--enrich` | LLM प्रमाणीकरण। MCP पर LLM-as-agent पथ के लिए आवश्यक नहीं। |
| `AUTOPAPERTOPPT_LLM_MODEL` | `--enrich` | डिफ़ॉल्ट `claude-opus-4-7` ओवरराइड। |
| `AUTOPAPERTOPPT_S2_API_KEY` | Semantic Scholar | उच्च दर सीमा। वैकल्पिक। |
| `AUTOPAPERTOPPT_NCBI_API_KEY` | PubMed | NCBI की अनाम सीमा (3/s) को 10/s तक बढ़ाता है। वैकल्पिक। |
| `AUTOPAPERTOPPT_CONTACT_EMAIL` | PubMed, ACM, Crossref, OpenAlex | अनुरोधों को Crossref के polite pool में रखता है। |
| `AUTOPAPERTOPPT_IEEE_API_KEY` | IEEE (API पथ) | आधिकारिक IEEE Xplore API; दायरे में आने वाले शोध-पत्रों के लिए `pdf_url` उजागर करता है। |
| `AUTOPAPERTOPPT_ENABLE_IEEE_SCRAPING` | IEEE (स्क्रैपिंग पथ) | `=1` स्क्रैपिंग सक्षम करता है। API key सेट होने पर आवश्यक नहीं। |
| `AUTOPAPERTOPPT_CROSSREF_PLUS_TOKEN` | ACM, Crossref | Crossref Plus ग्राहक टोकन (Bearer हेडर)। वैकल्पिक। |
| `AUTOPAPERTOPPT_SPRINGER_API_KEY` | Springer | अनिवार्य; मुफ्त कुंजी <https://dev.springernature.com/> से। इसके बिना plugin चुपचाप छोड़ दिया जाता है। |
| `AUTOPAPERTOPPT_ENABLE_SCHOLAR_SCRAPING` | Google Scholar | `=1` स्क्रैपिंग सक्षम करता है। डिफ़ॉल्ट बंद — Scholar ToS स्क्रैपिंग निषेध। |
| `AUTOPAPERTOPPT_PDF_COOKIES_FILE` | PDF डाउनलोडर | Netscape-स्वरूप `cookies.txt`। डिफ़ॉल्ट बंद। केवल उन प्रकाशकों के साथ उपयोग करें जिनके लिए आपके पास संस्थागत अधिकार हैं। |
| `AUTOPAPERTOPPT_LOG_LEVEL` | logger | डिफ़ॉल्ट `INFO`; विस्तृत ट्रेस के लिए `DEBUG`। |

डिफ़ॉल्ट: `--query` → `pptx,xlsx,bib`। `--paper` → `pptx,bib`। हमेशा स्पष्ट `--export` से ओवरराइड किया जा सकता है।

## MCP सर्वर

Claude Code के साथ पंजीकृत करें:

```powershell
claude mcp add autopapertoppt -- ".venv\Scripts\python.exe" -m autopapertoppt.mcp
```

या सेटिंग्स फ़ाइल को संपादित करें:

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

उपकरण:

| उपकरण | उद्देश्य |
|---|---|
| `list_sources` | प्रत्येक plugin की गणना + वर्तमान env में कौन से सक्षम हैं रिपोर्ट करें। `search` से पहले एक बार कॉल करें। |
| `search` | कीवर्ड → शोध-पत्र सूची। `top_tier_only`, `min_citations` स्वीकार करता है; डिफ़ॉल्ट पूरा API-key-रहित स्रोत मिश्रण। |
| `fetch_paper` | arXiv / DOI / PMID / IEEE पहचानकर्ता → एकल शोध-पत्र। |
| `fetch_pdf_text` | एक PDF डाउनलोड करें, निकाला गया मुख्य पाठ लौटाएँ। **"मैंने शोध-पत्र पढ़ा" तक का MCP पथ।** |
| `download_pdfs` | शोध-पत्र सूची की PDFs को `{out_dir}/pdfs/` में बैच डाउनलोड करें। BibTeX कुंजी द्वारा अनुक्रमित प्रति-शोध-पत्र परिणाम लौटाता है। |
| `export` | शोध-पत्र सूची + प्रारूप → `.pptx/.xlsx/.md/.bib/.json` लिखता है। प्रति-शोध-पत्र `summary` फ़ील्ड (rich thesis-style schema) और `max_slides_per_paper` (डिफ़ॉल्ट 25) स्वीकार करता है। |
| `pptx_inspect` | मौजूदा डेक की स्लाइड / शेप संरचना पढ़ें। |
| `pptx_update_slide` | `title` / `body` / `meta` (शेप नाम से) या मनमाने शेप (अनुक्रमणिका से) प्रतिस्थापित करें। |
| `pptx_delete_slide` | एक स्लाइड और उसका part relationship हटाएँ। |
| `pptx_reorder_slides` | `sldIdLst` के माध्यम से स्लाइड क्रम बदलें। |
| `pptx_add_slide` | अंत में जोड़ें या निर्दिष्ट स्थिति पर नई title / body / meta स्लाइड डालें। |

LLM-as-agent प्रवाह (`ANTHROPIC_API_KEY` की आवश्यकता नहीं — LLM ही एजेंट):

```
1. (वैकल्पिक) list_sources()                       # सक्षम plugins खोजें
2. search(keywords=..., sources=[...], top_tier_only=true)
3. (वैकल्पिक) download_pdfs(papers, out_dir="./exports/...")  # PDFs संग्रहीत करें
4. fetch_pdf_text(pdf_url=paper.pdf_url)           # प्रति शोध-पत्र
5. (LLM पाठ पढ़ता है, संरचित `summary` dict तैयार करता है)
6. export(papers=[{...paper, "summary": {pain_points: [...], rq_results: [...]}}],
          language="hi", formats=["pptx","bib"], ...)
```

पूर्ण संदर्भ [`docs/mcp.md`](docs/mcp.md) में।

## परियोजना संरचना

```
AutoPaperToPPT/
├── autopapertoppt/                 # मुख्य पैकेज
│   ├── core/                        # Paper / PaperSummary / RqResult / dedup / ranking / pipeline
│   ├── fetchers/                    # HTTPS-only async client, token-bucket rate limit
│   ├── exporters/                   # pptx (थीसिस-शैली) · xlsx · bib · md · json · pptx_edit · i18n
│   ├── intelligence/                # PDF डाउनलोड + Anthropic सारांश ([intelligence] extra)
│   ├── mcp/                         # FastMCP सर्वर (11 उपकरण)
│   ├── utils/                       # logging, path safety
│   ├── cli.py                       # argparse CLI
│   └── __main__.py
├── sources/                         # plugin फ़ोल्डर: arxiv, semantic_scholar,
│                                    #   openalex, pubmed, acm, ieee, scholar,
│                                    #   dblp, crossref, openaire, springer
├── tests/                           # pytest सूट + रिकॉर्डेड fixtures (कोई लाइव HTTP नहीं)
├── docs/                            # Sphinx (14 भाषा वृक्ष)
├── scripts/                         # एक-बार regen स्क्रिप्ट
└── pyproject.toml                   # ruff, bandit, build, वैकल्पिक extras
```

## Definition of Done

```powershell
.venv\Scripts\python.exe -m pytest tests/
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m bandit -c pyproject.toml -r autopapertoppt/ sources/
```

bandit का `-c` फ़्लैग अनिवार्य है — इसके बिना bandit परियोजना के skip कॉन्फ़िगरेशन को अनदेखा करता है। pptx एक्सपोर्टर को छूते समय, overflow जाँच भी चलाएँ (`CLAUDE.md` "Slide Deck Rules" देखें)।

## लाइसेंस

`LICENSE` देखें। arXiv API arXiv की उपयोग शर्तों (<https://info.arxiv.org/help/api/tou.html>) के तहत उपयोग की जाती है — हर 3 सेकंड में 1 अनुरोध की सॉफ्ट सीमा का पालन करें; बंडल किया गया fetcher पहले से ही token bucket के माध्यम से इस दर को लागू करता है।

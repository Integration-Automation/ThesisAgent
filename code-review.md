# 程式審核：ThesisAgents

## 審核者

- 審核者：工作區程式審核
- 日期：2026-10-22
- 對象：`ThesisAgents`（工作樹熱點：論文搜尋與簡報產生）
- 結論：需修正

## 審核規範

本次依下列 10 條審核。更嚴的專案門檻從嚴。

1. 設計：分層、失敗隔離、擴充點是否與 `architecture.md` 一致。
2. 可讀性：圈複雜度不超過 15、函式不超過 80 行、巢狀不超過 4、參數不超過 7、行寬不超過 120。專案若更嚴，以專案為準。
3. 錯誤處理：失敗要有邊界，不可裸吞例外。
4. 死碼：未使用的常數、分支與註解不得冒充已實作的行為。
5. 型別與 docstring：公開邊界要有型別與說明，且說明須與程式一致。
6. 安全：外部 HTTP、金鑰來源與是否寫死、命令注入、檔案路徑穿越。
7. 測試：風險路徑要有對應測試，且測試不能只覆蓋正例。
8. 效能：連線池、速率與併發是否會打爆上游或本機。
9. §6 契約：`architecture.md` 第 6 節的跨專案邊界不得被靜默打破。
10. 文件同步：環境變數、傳輸方式與行為描述須與程式一致。

嚴重度分缺陷、建議、備註。通過指沒有未關閉缺陷。有條件通過指沒有立即損害。需修正指仍有未關閉缺陷。

## 審核紀錄

### 方法

閱讀 `architecture.md`、`CLAUDE.md` 的專案概觀與網路／瀏覽器規則、`progress.md` 前 80 行，以及 `docs/configuration.md` 的環境變數表。在 `thesisagents/` 套件原始碼搜尋 `eval(`、`exec(`、`shell=True`、`pickle`、`yaml.load`、`verify=False`、裸 `except:`、`subprocess`、`api_key`、`password`、`token`，並排除 `tests/`、`docs/_build/`、`__pycache__/`。命中後逐檔閱讀 `fetchers/http.py`、`fetchers/webrunner_browser.py`、`fetchers/webrunner_pdf.py`、`fetchers/rate_limit.py`、`utils/path_safety.py`、`core/pdf_download.py`、`core/pdf_cookies.py`、`core/oa_resolver.py`、`core/identifiers.py`、`core/query.py`、`intelligence/pdf.py`、`intelligence/summarise.py`、`gui/pages/settings.py`、`mcp/server.py`、`exporters/pptx_edit.py`，以及各來源 fetcher 的金鑰與請求組裝。說明文件中的省略號占位不當成可用金鑰。未改其他檔、未執行測試、未啟動程式、未呼叫外部 API。

### 總評

搜尋與匯出的分層清楚：外部 HTTP 集中在 `get_client`，付費牆頁面另走可見 Chrome，匯出檔名有 slug，相對路徑有 `resolve_safe`。套件內沒有寫死的可用金鑰，也沒有命令注入。未關閉的問題是付費牆主機判斷用字串後綴，仿冒網域會被送進可能帶著使用者 Chrome 設定檔的瀏覽器。另有速率註解與實作不符，以及 PDF 第二跳缺少內網位址界限。

### 發現

#### CR-01

- 嚴重度：缺陷
- 位置：`thesisagents/fetchers/webrunner_pdf.py` 第 50 至 69 行、第 83 至 88 行。呼叫點在 `thesisagents/core/pdf_download.py` 第 140 至 142 行。瀏覽器選項在 `thesisagents/fetchers/webrunner_browser.py` 第 76 至 93 行。
- 說明：`should_use_webrunner` 用 `host.endswith(suffix)` 判斷付費牆。後綴沒有要求點邊界，因此 `evilieee.org` 會命中 `ieee.org`，`notacm.org` 會命中 `acm.org`，`notwiley.com`、`notoup.com`、`fakescience.org` 等同理。`pdf_url` 來自 OpenAlex、Semantic Scholar、Unpaywall、CORE，或 MCP `download_pdfs` 的呼叫端，不是固定主機清單。命中後 `download_via_browser` 會以可見 Chrome 開啟該 URL。若設定了 `THESISAGENTS_CHROME_PROFILE_DIR`，這個視窗使用使用者的 Chrome 設定檔，而且 `make_driver` 加上 `--no-sandbox`，PDF 下載偏好又把 Safe Browsing 設為關閉。瀏覽器本身的 cookie 網域比對仍有點邊界，不表示出版商 cookie 一定會被送到仿冒主機。風險是攻擊頁面跑在該設定檔與放寬過的 Chrome 裡。
- 依據：安全（外部 HTTP 與瀏覽器載入的主機範圍）。`architecture.md` 第 6 節要求外部服務只經 `fetchers/http.py` 或可見 Chrome 輔助，主機分類錯誤會把不該走 Chrome 的 URL 送進去。`tests/test_webrunner_pdf.py` 只斷言正例出版商與少數開放主機，沒有仿冒後綴的反例。
- 狀態：未關閉
- 建議：比對改為主機等於後綴，或主機以「點加後綴」結尾。為 `notieee.org` 這類名稱補反例測試。設定檔路徑只在通過比對後才套用。

#### CR-02

- 嚴重度：建議
- 位置：`thesisagents/core/pdf_download.py` 第 1 至 14 行與第 61 至 76、163 行。`thesisagents/core/oa_resolver.py` 第 61 至 68、193 至 207、241 至 253、286 至 300 行。`thesisagents/intelligence/pdf.py` 第 1 至 6、35 至 45 行。`thesisagents/fetchers/http.py` 第 70 至 76 行。`thesisagents/core/constants.py` 第 8 至 10 行。
- 說明：檔案註解寫 PDF 下載與 PDF 文字擷取沿用各來源的 token bucket。bucket 實際只在各 `sources/*/fetcher.py` 送搜尋請求前呼叫 `acquire`。`get_client` 只做 HTTPS 傳輸、逾時與連線池，`AsyncHTTPTransport(retries=0)`。`HTTP_MAX_RETRIES` 與 `HTTP_BACKOFF_BASE_SECONDS` 沒有其他讀取點，屬死碼。OA 解析另用 `unpaywall`、`semantic_scholar_oa`、`core_ac_uk` 三個 client 鍵，併發上限 5，不進入 Semantic Scholar 搜尋那條每秒 1 次的 bucket。PDF 下載併發上限 4，同樣不取得 bucket。`docs/configuration.md` 寫有金鑰時 Semantic Scholar 可到每秒 10 次、NCBI 可到每秒 10 次，對應 fetcher 仍固定每秒 1 次與每秒 3 次。這兩處程式比文件保守，不會因此超速。超速風險在 OA 與 PDF 這兩條旁路。
- 依據：死碼、文件與 docstring 不一致、效能與上游禮貌使用。搜尋路徑的 429 仍由 `core/pipeline.py` 做有限次退避，故不列為缺陷。
- 狀態：未關閉（建議）
- 建議：讓 PDF、OA 與文字擷取走與該上游相同的 bucket，或改寫註解，刪除未使用的重試常數。文件上的每秒 10 次若尚未實作，應改成與 `RateLimit` 相同的數字。

#### CR-03

- 嚴重度：建議
- 位置：`thesisagents/core/pdf_download.py` 第 171 至 178、196 至 211、249 至 266 行。`thesisagents/intelligence/pdf.py` 第 35 至 45 行。`thesisagents/mcp/server.py` 的 `fetch_pdf_text`（約第 231 至 245 行）。
- 說明：第一個 `pdf_url` 若不是付費牆主機，以及 HTML 裡 `citation_pdf_url` 的第二跳，都直接 `client.get`。第二跳用 `urljoin` 接上頁面給的位址，不再呼叫 `should_use_webrunner`。`HttpsOnlyTransport` 會拒絕非 HTTPS，包含重新導向後的非 HTTPS，這一點已讀過 `fetchers/http.py` 第 27 至 34 行。傳輸層不拒絕 loopback、鏈路本機或私有網段上的 HTTPS。cookie 只在 `pdf_cookies._domain_matches` 認為網域相符時附加，比對有前導點，沒有 CR-01 那種無點邊界的後綴錯誤。這不能阻止對使用者本機能連上的內網 HTTPS 服務發請求。MCP `fetch_pdf_text` 的 URL 由呼叫端給定，範圍相同。
- 依據：安全（外部 HTTP 的目標範圍）。公開 OA 主機不應整表封鎖，故不升為缺陷。
- 狀態：未關閉（建議）
- 建議：在送出前拒絕非 HTTPS，以及 loopback、鏈路本機與私有網段。第二跳若主機屬於付費牆清單，應與第一跳使用同一條瀏覽器路徑。

#### CR-04

- 嚴重度：建議
- 位置：`thesisagents/fetchers/webrunner_browser.py` 第 76 至 93 行。`thesisagents/sources/scholar/webrunner_backend.py` 第 97 至 114 行的 `_build_chrome_args` 同樣列出 `--no-sandbox`，實際啟動仍走 `make_driver`。
- 說明：每一個 Chrome 都加上 `--no-sandbox`。PDF 下載把 `safebrowsing.enabled` 設為 False。兩處都沒有說明為何使用者桌面上的可見視窗也要關掉沙箱與 Safe Browsing。此視窗會開啟出版商頁面，並在設定了 `THESISAGENTS_CHROME_PROFILE_DIR` 時載入該設定檔。CR-01 修正主機比對之後，這項放寬仍然存在。
- 依據：安全（瀏覽器載入外部頁面時的隔離）。未看到 `shell=True` 或把使用者字串拼進 shell，故不把這項寫成命令注入。
- 狀態：未關閉（建議）
- 建議：桌面路徑不要加 `--no-sandbox`，除非有註明僅限無法使用沙箱的環境。PDF 下載不要關掉 Safe Browsing。若必須保留，在 `make_driver` 的 docstring 寫明失敗模式與適用範圍。

#### CR-05

- 嚴重度：備註
- 位置：`thesisagents/fetchers/http.py` 第 61 至 67 行。`docs/configuration.md` 環境變數表中 `THESISAGENTS_CONTACT_EMAIL` 那一列（約第 37 行）。
- 說明：預設 User-Agent 寫死「set THESISAGENTS_CONTACT」。程式與 `docs/configuration.md`、`architecture.md` 使用的名稱是 `THESISAGENTS_CONTACT_EMAIL`，而且 User-Agent 並不讀取該變數。郵件實際由 OpenAlex、Crossref、ACM 的 `mailto`、PubMed 的 `email` 查詢參數，以及 Unpaywall 的 `email` 參數送出。同一列文件把 NCBI 的 `tool` 與 `email` 寫成標頭。`thesisagents/sources/pubmed/fetcher.py` 第 98 至 102 行把它們放在查詢參數，這與 E-utilities 的用法一致，是文件用詞錯誤，不是多送了一份金鑰。
- 依據：文件同步。不外洩金鑰，也不改變 HTTPS 限制。
- 狀態：未關閉（備註）
- 建議：User-Agent 改為真實的變數名稱，或在有設定聯絡郵件時放入郵件。文件改為查詢參數。

沒有其他已確認的缺陷。命令注入、寫死可用金鑰、路徑穿越未成立，見下方已核對。

### 已核對

- 金鑰來源：Anthropic、Semantic Scholar、NCBI、IEEE、Springer、Crossref Plus、CORE 都在使用當下從環境變數讀取。GUI 的 `thesisagents/gui/pages/settings.py` 把同一批值存進本機 QSettings，啟動時寫回 `os.environ`。`docs/configuration.md` 已寫明 Windows 登錄、macOS plist 與 Linux ini 的位置，介面文案也寫本機儲存。這是明文使用者設定，不是原始碼裡的可用金鑰。空字串會清掉環境變數。說明文件裡的 Anthropic 範例是省略號占位，不當缺陷。
- 金鑰放置：Semantic Scholar 與 OA 的 S2 查詢使用 `x-api-key`。CORE 與 Crossref Plus 使用標頭。Anthropic 金鑰交給官方客戶端。IEEE、Springer、NCBI 依上游介面把金鑰放在查詢參數。套件日誌沒有主動印出這些值。4xx 會把回應本文前 256 字元放進例外。本次未看到上游一定會把查詢字串回顯，故不列缺陷。
- 傳輸：套件內的 `httpx` 呼叫都經過 `get_client`。`HttpsOnlyTransport` 拒絕非 `https`。`follow_redirects=True` 時，後續請求仍經過同一層包裝。未看到 `verify=False`、`requests`、`urlopen`。arXiv 與 PubMed 的 XML 使用 `defusedxml`。
- 命令注入：套件內沒有 `subprocess`、`shell=True`、`os.system`、`pickle`、`yaml.load` 或裸 `except:`。`gui/app.py` 的 `app.exec()` 是 Qt 事件迴圈。IEEE 的 `execute_async_script` 把 URL 與 JSON 當引數傳入，沒有把使用者關鍵字拼進腳本文字。Scholar 查詢使用 `urlencode`。Chrome 參數是固定清單，設定檔路徑是單一 `add_argument`，不是 shell。`scripts/migrate_sources_into_package.py` 的 `subprocess.run` 接收字串清單且不在安裝套件內，不列缺陷。
- 路徑：`resolve_safe` 拒絕絕對路徑、`..` 與解析後逃出根目錄的符號連結。匯出檔名經 `safe_filename`，斜線與 `..` 進不了檔名。`ensure_export_dir` 允許呼叫端指定的輸出目錄，這是 CLI 與 MCP 的輸出位置，不是把相對路徑拼進根目錄。`pptx_edit` 依呼叫端給的路徑開關簡報，屬本機編輯工具的設計。
- 輸入：關鍵字經 `normalize_query` 去掉控制字元並限制長度。DOI、PMID、arXiv、IEEE 編號在 `identifiers.py` 有格式判斷後才分派。
- 錯誤處理：廣泛的 `except Exception` 多半帶 `BLE001` 與邊界理由（單一來源失敗不拖垮整批、PDF 與 OA 為盡力而為）。不是裸 `except:`。
- §6：沒有依賴工作區的 WebRunner 套件。Selenium 由 `webrunner_browser.py` 每個呼叫各開一個 Chrome。除 CR-01 的主機分類外，外部服務仍只經共用 HTTP client 或該瀏覽器輔助。
- `progress.md` 前 80 行只有未完成的評測集與 Nuitka 快取兩項，與本次熱點無直接衝突。

### 未涵蓋

- 未執行 pytest、ruff、bandit，也未逐函式計算圈複雜度與行數。`thesisagents/exporters/pptx.py` 體積大，不在本次 HTTP 與路徑熱點的逐行範圍。
- 未對照已安裝的 httpx 是否在標頭含換行時拒絕請求，因此不對 cookie 值拼進 `Cookie` 標頭下結論。
- 未審查 `docs/_build/`、測試假金鑰、以及 `scripts/` 裡簡報維護腳本的簡報內容。
- 未連線驗證各上游是否在錯誤本文回顯查詢字串。

### 本專案加嚴

`pyproject.toml` 的 ruff 行寬是 100，McCabe 上限是 10，都嚴於本規範的 120 與 15。本次未跑 linter，不宣稱全套件達標。網路與路徑另有專案自己的約定：全部 HTTP 走 `get_client`、付費牆走可見 Chrome、匯出檔名走 `safe_filename`。CR-01 與 CR-02 就是對照這些約定後的差距。

### 結論

需修正。發現 5 則：缺陷 1（CR-01，未關閉）、建議 3（CR-02、CR-03、CR-04）、備註 1（CR-05）。沒有寫死的可用金鑰，套件內也沒有命令注入或已成立的路徑穿越。CR-01 未關，故不能通過，也不能有條件通過。

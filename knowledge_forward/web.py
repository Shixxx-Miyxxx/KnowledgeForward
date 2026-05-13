INDEX_HTML_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Chat</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #1e1e1e;
      --panel: #262626;
      --panel-strong: #2a2a2a;
      --input: #1a1a1a;
      --line: #3a3a3a;
      --text: #dcddde;
      --muted: #a0a0a0;
      --muted-strong: #c4c4c4;
      --accent: #8b5cf6;
      --accent-strong: #a78bfa;
      --accent-dark: #33294a;
      --danger: #f87171;
      --ok: #7dd3fc;
      --shadow: rgba(0, 0, 0, 0.38);
      --composer-height: 104px;
      --keyboard-offset: 0px;
      --radius-sm: 14px;
      --radius-md: 20px;
      --radius-lg: 28px;
    }

    * { box-sizing: border-box; }

    [hidden] { display: none !important; }

    html {
      height: 100%;
      overflow-x: hidden;
      overflow-y: hidden;
      overscroll-behavior: none;
    }

    body {
      position: fixed;
      inset: 0;
      width: 100%;
      height: 100%;
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 16px;
      line-height: 1.5;
      overflow-x: hidden;
      overflow-y: hidden;
      overscroll-behavior: none;
    }

    button, input, textarea, select {
      font: inherit;
    }

    button {
      min-height: 44px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel-strong);
      color: var(--text);
      padding: 9px 12px;
      font-weight: 650;
      touch-action: manipulation;
    }

    button.primary {
      border-color: var(--accent);
      background: var(--accent);
      color: #ffffff;
    }

    button.ghost {
      background: transparent;
      color: var(--muted-strong);
    }

    button.icon {
      width: 46px;
      padding: 0;
      display: inline-grid;
      place-items: center;
      flex: 0 0 auto;
    }

    button:disabled, input:disabled, textarea:disabled, select:disabled {
      opacity: 0.55;
    }

    input, textarea, select {
      width: 100%;
      max-width: 100%;
      min-width: 0;
      min-height: 44px;
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: var(--input);
      color: var(--text);
      padding: 10px 12px;
      outline: none;
    }

    input:focus, textarea:focus, select:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.22);
    }

    textarea {
      resize: none;
    }

    label {
      display: block;
      color: var(--muted);
      font-size: 0.88rem;
      margin: 0 0 6px;
    }

    .app {
      position: fixed;
      inset: 0;
      overflow: hidden;
    }

    .chat-history {
      position: absolute;
      top: 0;
      left: 50%;
      bottom: calc(var(--composer-height) + var(--keyboard-offset));
      transform: translateX(-50%);
      width: min(820px, 100%);
      margin: 0 auto;
      padding: calc(18px + env(safe-area-inset-top)) 12px 26px;
      overflow-y: auto;
      overflow-x: hidden;
      overscroll-behavior: contain;
      -webkit-overflow-scrolling: touch;
    }

    .empty-state {
      display: none;
    }

    .message-row {
      display: flex;
      margin: 0 0 14px;
    }

    .message-row.user {
      justify-content: flex-end;
    }

    .message-row.assistant, .message-row.search, .message-row.error {
      justify-content: flex-start;
    }

    .message-bubble {
      max-width: min(92%, 680px);
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      padding: 11px 12px;
      overflow-wrap: anywhere;
      white-space: pre-wrap;
      box-shadow: 0 8px 24px var(--shadow);
    }

    .message-bubble.user {
      background: #302748;
      border-color: #4a3b6b;
      color: #f0ecff;
    }

    .message-bubble.assistant {
      background: var(--panel);
    }

    .message-bubble.search {
      background: #222631;
      border-color: #394154;
    }

    .message-bubble.error {
      background: #332323;
      border-color: #744141;
      color: #fecaca;
    }

    .message-label {
      color: var(--accent-strong);
      font-size: 0.82rem;
      font-weight: 700;
      margin-bottom: 7px;
      white-space: normal;
    }

    .loading-dots {
      color: var(--muted-strong);
    }

    .message-bubble.thinking {
      border: 0;
      border-radius: 0;
      background: transparent;
      box-shadow: none;
      padding: 2px 0 2px 8px;
      color: var(--muted-strong);
      animation: thinkingPulse 1.35s ease-in-out infinite;
    }

    @keyframes thinkingPulse {
      0%, 100% {
        opacity: 0.45;
      }
      50% {
        opacity: 1;
      }
    }

    .applied-inline {
      margin-top: 10px;
      color: var(--muted);
      font-size: 0.84rem;
      white-space: normal;
    }

    .results-list {
      display: grid;
      gap: 9px;
      margin-top: 10px;
      min-width: 0;
      max-width: 100%;
      overflow-x: hidden;
    }

    .result-item, .citation-item {
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: rgba(255, 255, 255, 0.025);
      padding: 9px;
      min-width: 0;
      max-width: 100%;
      overflow-x: hidden;
      overflow-wrap: anywhere;
      word-break: break-word;
      white-space: normal;
    }

    .result-title, .citation-title {
      font-weight: 700;
      margin-bottom: 4px;
      min-width: 0;
      max-width: 100%;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .citation-header {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }

    .citation-header .citation-title {
      flex: 1 1 auto;
      margin-bottom: 0;
    }

    button.copy-source {
      min-height: 30px;
      width: 30px;
      height: 30px;
      padding: 0;
      border: 0;
      border-radius: 8px;
      background: transparent;
      color: var(--muted);
      line-height: 1;
      flex: 0 0 auto;
      display: inline-grid;
      place-items: center;
    }

    button.copy-source:hover {
      background: rgba(255, 255, 255, 0.06);
      color: var(--muted-strong);
    }

    button.copy-source.copied {
      color: var(--accent-strong);
    }

    .copy-source .icon-svg {
      width: 18px;
      height: 18px;
      color: currentColor;
    }

    .meta {
      color: var(--muted);
      font-size: 0.82rem;
      min-width: 0;
      max-width: 100%;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .snippet {
      margin-top: 7px;
      color: var(--muted-strong);
      font-size: 0.9rem;
      min-width: 0;
      max-width: 100%;
      overflow-wrap: anywhere;
      word-break: break-word;
      white-space: pre-wrap;
    }

    .answer-footer {
      margin-top: 10px;
      border-top: 1px solid var(--line);
      padding-top: 8px;
      color: var(--muted);
      font-size: 0.9rem;
      white-space: normal;
    }

    .answer-footer-line {
      min-height: 28px;
      display: flex;
      align-items: center;
    }

    details.source-details {
      margin-top: 2px;
      white-space: normal;
    }

    details.source-details summary {
      color: var(--muted-strong);
      cursor: pointer;
      min-height: 34px;
      display: flex;
      align-items: center;
    }

    .composer-wrap {
      position: fixed;
      left: 0;
      right: 0;
      bottom: var(--keyboard-offset);
      z-index: 25;
      background: var(--bg);
      padding: 8px 12px calc(14px + env(safe-area-inset-bottom));
      backdrop-filter: blur(18px);
      transition: bottom 0.16s ease;
    }

    .composer-inner {
      width: min(820px, 100%);
      margin: 0 auto;
    }

    .composer {
      display: grid;
      grid-template-rows: minmax(44px, auto) 42px;
      gap: 4px;
      align-items: stretch;
      min-height: 108px;
      border: 1px solid var(--line);
      border-radius: 30px;
      background: var(--input);
      padding: 10px;
      box-shadow: 0 10px 26px var(--shadow);
    }

    .composer-tools {
      display: inline-flex;
      align-items: center;
      justify-content: flex-start;
      gap: 2px;
      height: 42px;
      min-width: 128px;
      max-width: 164px;
      border: 1px solid rgba(139, 92, 246, 0.45);
      border-radius: 999px;
      background: transparent;
      padding: 0 5px 0 2px;
    }

    .input-shell {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr) 42px;
      gap: 6px;
      align-items: center;
      min-height: 42px;
      background: transparent;
    }

    .composer textarea {
      min-height: 44px;
      max-height: 132px;
      border: 0;
      background: transparent;
      padding: 4px 8px;
      box-shadow: none;
      line-height: 1.35;
    }

    .composer textarea:focus {
      border-color: transparent;
      box-shadow: none;
    }

    .composer-button {
      width: 42px;
      height: 42px;
      min-height: 42px;
      border: 0;
      border-radius: 999px;
      background: transparent;
      color: var(--accent-strong);
      padding: 0;
      line-height: 1;
    }

    .icon-svg {
      display: block;
      width: 24px;
      height: 24px;
      margin: 0 auto;
      color: var(--accent-strong);
      stroke: currentColor;
      stroke-width: 2.25;
      stroke-linecap: round;
      stroke-linejoin: round;
      fill: none;
    }

    .period-button {
      display: inline-flex;
      align-items: center;
      justify-content: flex-start;
      gap: 4px;
      max-width: 110px;
      min-height: 38px;
      height: 38px;
      border: 0;
      border-radius: 999px;
      background: transparent;
      color: var(--accent-strong);
      padding: 0 4px 0 0;
      font-size: 0.92rem;
      font-weight: 400;
      line-height: 1;
      white-space: nowrap;
      transform: translateY(0);
    }

    .period-button span:first-child {
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .period-chevron {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 14px;
      height: 14px;
      color: var(--accent-strong);
      font-size: 1rem;
      line-height: 1;
      transform: translateY(-3px);
    }

    .period-chevron::before {
      content: "";
      width: 8px;
      height: 8px;
      border-right: 2px solid currentColor;
      border-bottom: 2px solid currentColor;
      transform: rotate(45deg);
    }

    .send-button {
      width: 42px;
      height: 42px;
      min-height: 42px;
      border: 0;
      border-radius: 999px;
      background: #4a4a4a;
      color: var(--muted);
      padding: 0;
      font-size: 1.25rem;
      font-weight: 800;
      line-height: 1;
    }

    .input-shell .send-button {
      grid-column: 3;
      justify-self: end;
    }

    .send-button:disabled {
      background: #4a4a4a;
      color: var(--muted);
    }

    .send-button.ready {
      background: var(--accent);
      color: #ffffff;
    }

    .toggle-track {
      display: inline-flex;
      align-items: center;
      align-self: center;
      justify-self: center;
      grid-column: 2;
      flex: 0 0 auto;
      width: 34px;
      height: 20px;
      border-radius: 999px;
      background: #171717;
      border: 1px solid var(--line);
      padding: 2px;
      transition: background 0.18s ease, border-color 0.18s ease;
    }

    .toggle-thumb {
      display: block;
      width: 14px;
      height: 14px;
      border-radius: 999px;
      background: var(--muted);
      transition: transform 0.18s ease, background 0.18s ease;
    }

    .overlay {
      position: fixed;
      inset: 0;
      z-index: 40;
      background: rgba(0, 0, 0, 0.5);
    }

    .period-overlay {
      position: fixed;
      inset: 0;
      z-index: 34;
      background: transparent;
    }

    .period-menu {
      position: fixed;
      left: max(62px, calc((100% - 820px) / 2 + 62px));
      bottom: calc(var(--keyboard-offset) + var(--composer-height) + 6px);
      z-index: 36;
      width: min(190px, calc(100% - 76px));
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: var(--panel-strong);
      box-shadow: 0 18px 48px var(--shadow);
      padding: 6px;
    }

    .command-menu {
      position: fixed;
      left: max(12px, calc((100% - 820px) / 2 + 12px));
      bottom: calc(var(--keyboard-offset) + var(--composer-height) + 8px);
      z-index: 36;
      width: min(420px, calc(100% - 24px));
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: var(--panel-strong);
      box-shadow: 0 18px 48px var(--shadow);
      padding: 6px;
    }

    .command-option {
      display: flex;
      align-items: center;
      width: 100%;
      min-height: 42px;
      border: 0;
      border-radius: var(--radius-sm);
      background: transparent;
      color: var(--text);
      padding: 7px 10px;
      text-align: left;
      font-size: 0.95rem;
      font-weight: 500;
    }

    .command-option:hover, .command-option:focus {
      background: rgba(255, 255, 255, 0.06);
    }

    .command-name {
      color: var(--accent-strong);
      font-weight: 700;
      overflow-wrap: anywhere;
    }

    .period-option {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      height: 38px;
      min-height: 38px;
      border: 0;
      border-radius: var(--radius-sm);
      background: transparent;
      color: var(--text);
      padding: 5px 10px;
      text-align: left;
      font-size: 0.95rem;
      font-weight: 400;
    }

    .period-option.active {
      background: var(--accent-dark);
      color: #ffffff;
    }

    .sheet-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 16px;
    }

    .sheet-header h2 {
      margin: 0;
      font-size: 1rem;
      letter-spacing: 0;
    }

    .button-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 10px;
    }

    .filter-sheet {
      position: fixed;
      left: 0;
      right: 0;
      bottom: var(--keyboard-offset);
      z-index: 45;
      width: 100%;
      max-width: 100vw;
      max-height: min(82vh, calc(100vh - var(--keyboard-offset) - 24px), 720px);
      background: var(--panel);
      border-top: 1px solid var(--line);
      border-radius: var(--radius-lg) var(--radius-lg) 0 0;
      padding: 14px 14px calc(16px + env(safe-area-inset-bottom));
      box-shadow: 0 -18px 42px var(--shadow);
      overflow-y: auto;
      overflow-x: hidden;
    }

    .filter-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 11px;
      max-width: 100%;
      overflow-x: hidden;
    }

    .filter-grid > div {
      min-width: 0;
    }

    .custom-date-field[hidden] {
      display: none !important;
    }

    input[type="date"] {
      -webkit-appearance: none;
      appearance: none;
      text-align: left;
      justify-content: flex-start;
    }

    input[type="date"]::-webkit-calendar-picker-indicator {
      display: none;
      opacity: 0;
    }

    input[type="date"]::-webkit-date-and-time-value {
      text-align: left;
    }

    .filter-status {
      min-height: 22px;
      color: var(--danger);
      font-size: 0.86rem;
      margin-top: 8px;
    }

    .visually-hidden {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }

    .token-dialog {
      position: fixed;
      left: 50%;
      top: 50%;
      z-index: 45;
      width: min(380px, calc(100% - 28px));
      transform: translate(-50%, -50%);
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: var(--panel);
      box-shadow: 0 22px 60px var(--shadow);
      padding: 18px;
    }

    .token-dialog h2 {
      margin: 0 0 14px 1px;
      font-size: 1rem;
      letter-spacing: 0;
    }

    .token-input-shell {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 58px;
      gap: 6px;
      align-items: center;
      min-height: 52px;
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: var(--input);
      padding: 4px 5px 4px 10px;
    }

    .token-input-shell:focus-within {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.22);
    }

    .token-input-shell input {
      min-height: 42px;
      border: 0;
      background: transparent;
      padding: 6px 0;
      box-shadow: none;
    }

    .token-input-shell input:focus {
      border-color: transparent;
      box-shadow: none;
    }

    .token-save-button {
      width: 42px;
      height: 42px;
      min-height: 42px;
      justify-self: end;
    }

    .token-error {
      min-height: 20px;
      margin: 10px 2px 0;
      color: var(--danger);
      font-size: 0.9rem;
      overflow-wrap: anywhere;
    }

    @media (min-width: 720px) {
      .chat-history { padding-left: 22px; padding-right: 22px; }
      .composer-wrap { padding-left: 18px; padding-right: 18px; }
      .filter-sheet {
        left: 50%;
        right: auto;
        width: min(760px, calc(100% - 28px));
        transform: translateX(-50%);
        border: 1px solid var(--line);
        border-bottom: 0;
      }
      .filter-grid {
        grid-template-columns: repeat(3, 1fr);
      }
      .filter-grid .wide {
        grid-column: span 3;
      }
    }

    @media (max-width: 430px) {
      .composer {
        min-height: 108px;
      }
      .composer-tools {
        min-width: 126px;
        max-width: 152px;
      }
    }

    #closeFilterButton {
      border-color: rgba(139, 92, 246, 0.45);
      color: var(--accent-strong);
    }
  </style>
</head>
<body>
  <div class="app">
    <div id="statusLine" class="visually-hidden" aria-live="polite"></div>

    <main id="chatHistory" class="chat-history" aria-live="polite">
      <div id="emptyState" class="empty-state">Ready.</div>
    </main>

    <div class="composer-wrap">
      <div class="composer-inner">
        <form id="composer" class="composer">
          <label class="visually-hidden" for="chatInput">チャット入力</label>
          <textarea id="chatInput" rows="1" autocomplete="off" placeholder="質問する"></textarea>
          <div class="input-shell">
            <div class="composer-tools">
              <button id="filterButton" class="composer-button" type="button" aria-label="filter設定を開く">
                <svg class="icon-svg" aria-hidden="true" viewBox="0 0 24 24">
                  <path d="M3 6h18"></path>
                  <path d="M7 12h10"></path>
                  <path d="M10 18h4"></path>
                </svg>
              </button>
              <button id="periodButton" class="period-button" type="button" aria-label="Periodを選択">
                <span id="periodButtonText">直近30日</span>
                <span class="period-chevron" aria-hidden="true"></span>
              </button>
            </div>
            <button id="sendButton" class="send-button" type="submit" aria-label="送信">↑</button>
          </div>
        </form>
      </div>
    </div>
  </div>

  <div id="periodOverlay" class="period-overlay" hidden></div>
  <section id="commandMenu" class="command-menu" aria-label="slash commands" hidden></section>
  <section id="periodMenu" class="period-menu" aria-label="period presets" hidden>
    <button class="period-option" type="button" data-period="today">今日</button>
    <button class="period-option" type="button" data-period="yesterday">昨日</button>
    <button class="period-option" type="button" data-period="last_7">直近7日</button>
    <button class="period-option" type="button" data-period="last_30">直近30日</button>
    <button class="period-option" type="button" data-period="last_90">直近90日</button>
    <button class="period-option" type="button" data-period="this_month">今月</button>
    <button class="period-option" type="button" data-period="this_year">今年</button>
    <button class="period-option" type="button" data-period="custom">カスタム</button>
    <button class="period-option" type="button" data-period="all_time">全期間</button>
  </section>

  <div id="tokenOverlay" class="overlay" hidden></div>
  <section id="tokenDialog" class="token-dialog" role="dialog" aria-modal="true" aria-labelledby="tokenTitle" hidden>
    <h2 id="tokenTitle">Token</h2>
    <div class="token-input-shell">
      <input id="token" type="password" autocomplete="current-password" placeholder="API token" aria-label="Token">
      <button id="saveTokenButton" class="token-save-button send-button ready" type="button" aria-label="Save">↑</button>
    </div>
    <div id="tokenError" class="token-error" aria-live="polite" hidden></div>
  </section>

  <div id="filterOverlay" class="overlay" hidden></div>
  <section id="filterPanel" class="filter-sheet" role="dialog" aria-modal="true" aria-labelledby="filterTitle" hidden>
    <div class="sheet-header">
      <h2 id="filterTitle">Filter</h2>
      <button id="closeFilterButton" class="ghost" type="button">Close</button>
    </div>

    <div class="filter-grid">
      <div>
        <label for="preset">Period</label>
        <select id="preset">
          <option value="today">今日</option>
          <option value="yesterday">昨日</option>
          <option value="last_7">直近7日</option>
          <option value="last_30">直近30日</option>
          <option value="last_90">直近90日</option>
          <option value="this_month">今月</option>
          <option value="this_year">今年</option>
          <option value="custom">カスタム</option>
          <option value="all_time">全期間</option>
        </select>
      </div>
      <div id="dateFromField" class="custom-date-field" hidden>
        <label for="dateFrom">From</label>
        <input id="dateFrom" type="date">
      </div>
      <div id="dateToField" class="custom-date-field" hidden>
        <label for="dateTo">To</label>
        <input id="dateTo" type="date">
      </div>
      <div>
        <label for="tags">tags</label>
        <input id="tags" type="text" autocomplete="off" placeholder="idea, want">
      </div>
      <div>
        <label for="sourceNames">Source</label>
        <input id="sourceNames" type="text" autocomplete="off" placeholder="user_notes">
      </div>
    </div>
    <div id="filterStatus" class="filter-status"></div>
  </section>

  <script>
    const TOKEN_STORAGE_KEY = "knowledgeforward_token";
    const FILTER_STORAGE_KEY = "knowledgeforward_filters";
    const INVALID_TOKEN_MESSAGE = "This token is invalid.";
    const API_PATHS = Object.freeze({
      health: "/health",
      reindex: "/reindex",
      search: "/search",
      ask: "/ask"__DEV_SECURITY_API_PATH__
    });
    const COMMANDS = Object.freeze([
      { name: "/reindex", insertText: "/reindex" },
      { name: "/diagnostics", insertText: "/diagnostics" }__DEV_SECURITY_COMMAND__
    ]);
    const DEFAULT_FILTERS = Object.freeze({
      preset: "last_30",
      dateFrom: "",
      dateTo: "",
      tags: "",
      sourceNames: ""
    });
    const PRESET_LABELS = {
      today: "今日",
      yesterday: "昨日",
      last_7: "直近7日",
      last_30: "直近30日",
      last_90: "直近90日",
      this_month: "今月",
      this_year: "今年",
      custom: "カスタム",
      all_time: "全期間"
    };

    const tokenInput = document.getElementById("token");
    const saveTokenButton = document.getElementById("saveTokenButton");
    const chatInput = document.getElementById("chatInput");
    const chatHistory = document.getElementById("chatHistory");
    const emptyState = document.getElementById("emptyState");
    const statusLine = document.getElementById("statusLine");
    const sendButton = document.getElementById("sendButton");
    const filterButton = document.getElementById("filterButton");
    const composer = document.getElementById("composer");
    const periodButton = document.getElementById("periodButton");
    const periodButtonText = document.getElementById("periodButtonText");
    const composerWrap = document.querySelector(".composer-wrap");

    const commandMenu = document.getElementById("commandMenu");
    const periodOverlay = document.getElementById("periodOverlay");
    const periodMenu = document.getElementById("periodMenu");
    const tokenOverlay = document.getElementById("tokenOverlay");
    const tokenDialog = document.getElementById("tokenDialog");
    const tokenError = document.getElementById("tokenError");

    const filterOverlay = document.getElementById("filterOverlay");
    const filterPanel = document.getElementById("filterPanel");
    const filterStatus = document.getElementById("filterStatus");
    const presetInput = document.getElementById("preset");
    const dateFromField = document.getElementById("dateFromField");
    const dateToField = document.getElementById("dateToField");
    const dateFromInput = document.getElementById("dateFrom");
    const dateToInput = document.getElementById("dateTo");
    const tagsInput = document.getElementById("tags");
    const sourceNamesInput = document.getElementById("sourceNames");

    let busy = false;
    let initialReindexPending = true;
    let initialReindexStarted = false;

    tokenInput.value = loadToken();
    let filtersState = loadFilters();
    writeFilterDraft(filtersState);
    syncPreset();
    renderFilterSummary();
    updateSendState();
    updateViewportLayout();
    if (!tokenInput.value.trim()) {
      openTokenDialog();
    } else {
      maybeStartInitialReindex();
    }

    saveTokenButton.addEventListener("click", saveToken);
    filterButton.addEventListener("click", openFilterPanel);
    commandMenu.addEventListener("pointerdown", event => {
      const option = event.target.closest("[data-command]");
      if (!option) return;
      event.preventDefault();
      selectCommand(option.dataset.command);
    });
    periodButton.addEventListener("click", togglePeriodMenu);
    periodOverlay.addEventListener("click", closePeriodMenu);
    for (const option of periodMenu.querySelectorAll("[data-period]")) {
      option.addEventListener("click", () => selectPeriod(option.dataset.period));
    }
    document.getElementById("closeFilterButton").addEventListener("click", closeFilterPanel);
    filterOverlay.addEventListener("click", closeFilterPanel);
    presetInput.addEventListener("change", syncPreset);

    composer.addEventListener("submit", handleSubmit);
    chatHistory.addEventListener("pointerdown", dismissKeyboardFromChatHistory);
    chatInput.addEventListener("input", () => {
      autoResizeInput();
      updateSendState();
      updateCommandMenu();
    });
    chatInput.addEventListener("focus", () => {
      updateCommandMenu();
      updateViewportLayout();
      scrollToBottom();
    });
    chatInput.addEventListener("blur", () => {
      setTimeout(() => {
        closeCommandMenu();
        updateViewportLayout();
      }, 80);
    });
    window.addEventListener("resize", updateViewportLayout);
    window.addEventListener("orientationchange", () => setTimeout(updateViewportLayout, 250));
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", updateViewportLayout);
      window.visualViewport.addEventListener("scroll", updateViewportLayout);
    }

    function headers(token = tokenInput.value) {
      const authToken = String(token || "").trim();
      return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${authToken}`
      };
    }

    async function handleSubmit(event) {
      event.preventDefault();
      if (busy) return;

      const rawText = chatInput.value.trim();
      if (!rawText) return;
      if (!tokenInput.value.trim()) {
        const row = appendAssistantPlaceholder("Tokenが必要です。");
        replaceWithError(row, new Error("Tokenが未入力、または認証に失敗しました。"));
        openTokenDialog();
        return;
      }

      if (rawText.toLowerCase() === "/reindex") {
        closeCommandMenu();
        appendUserMessage(rawText);
        chatInput.value = "";
        autoResizeInput();
        updateSendState();
        const row = appendThinkingPlaceholder("Reindex中");
        setBusy(true);
        try {
          const data = await callReindex();
          replaceWithSystemMessage(row, formatReindexResult(data));
        } catch (error) {
          replaceWithError(row, error);
        } finally {
          setBusy(false);
          chatInput.focus();
        }
        return;
      }

      if (rawText.toLowerCase().startsWith("/diagnostics")) {
        closeCommandMenu();
        const query = rawText.slice("/diagnostics".length).trim();
        appendUserMessage(rawText);
        chatInput.value = "";
        autoResizeInput();
        updateSendState();
        const row = appendThinkingPlaceholder("Diagnostics中");
        setBusy(true);
        try {
          if (!query) throw new Error("使い方: /diagnostics <query>");
          const data = await postJson(API_PATHS.search, {
            query,
            offset: 0,
            page_size: 50,
            filters: buildFilters()
          });
          replaceWithDiagnostics(row, data);
        } catch (error) {
          replaceWithError(row, error);
        } finally {
          setBusy(false);
          chatInput.focus();
        }
        return;
      }

__DEV_SECURITY_HANDLER__

      if (rawText.startsWith("/")) {
        closeCommandMenu();
        appendUserMessage(rawText);
        chatInput.value = "";
        autoResizeInput();
        updateSendState();
        const row = appendAssistantPlaceholder("Commandを確認しています...");
        replaceWithError(row, new Error("Unknown command."));
        return;
      }

      closeCommandMenu();
      appendUserMessage(rawText);
      chatInput.value = "";
      autoResizeInput();
      updateSendState();
      const row = appendThinkingPlaceholder();
      setBusy(true);

      try {
        const filters = buildFilters();
        const data = await postJson(API_PATHS.ask, { question: rawText, filters });
        replaceWithAnswer(row, data);
        statusLine.textContent = data.used_ollama ? "answered" : "no evidence";
      } catch (error) {
        replaceWithError(row, error);
        statusLine.textContent = "error";
      } finally {
        setBusy(false);
        chatInput.focus();
      }
    }

    async function callReindex() {
      if (!tokenInput.value.trim()) {
        openTokenDialog();
        throw new Error("Tokenが必要です。");
      }
      statusLine.textContent = "indexing";
      try {
        const data = await fetch(API_PATHS.reindex, { method: "POST", headers: headers() }).then(readResponse);
        statusLine.textContent = "indexed";
        return data;
      } catch (error) {
        statusLine.textContent = "error";
        throw error;
      }
    }

    async function postJson(path, payload) {
      return fetch(path, { method: "POST", headers: headers(), body: JSON.stringify(payload) }).then(readResponse);
    }

    async function readResponse(response) {
      const text = await response.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch { data = {}; }
      if (!response.ok) {
        if (response.status === 401) {
          handleAuthFailure();
        }
        throw new Error(messageForStatus(response.status, data));
      }
      return data;
    }

    function messageForStatus(status, data) {
      if (status === 400) return "Filterまたは入力内容を確認してください。";
      if (status === 401) return INVALID_TOKEN_MESSAGE;
      if (status === 409) return data && data.detail ? sanitizeDisplayText(data.detail) : "/reindex を実行してください。";
      if (status === 422) return "入力内容を確認してください。";
      if (status === 502) return "回答生成に失敗しました。Ollamaの状態を確認してください。";
      return `APIエラーが発生しました。(${status})`;
    }

    function maybeStartInitialReindex() {
      if (!initialReindexPending || initialReindexStarted || !tokenInput.value.trim()) return;
      initialReindexPending = false;
      initialReindexStarted = true;
      requestAnimationFrame(() => {
        callReindex().catch(() => {
          statusLine.textContent = "error";
        });
      });
    }

    function appendUserMessage(text) {
      removeEmptyState();
      const row = document.createElement("article");
      row.className = "message-row user";
      const bubble = document.createElement("div");
      bubble.className = "message-bubble user";
      bubble.textContent = sanitizeDisplayText(text);
      row.appendChild(bubble);
      chatHistory.appendChild(row);
      scrollToBottom();
    }

    function appendAssistantPlaceholder(text) {
      removeEmptyState();
      const row = document.createElement("article");
      row.className = "message-row assistant";
      const bubble = document.createElement("div");
      bubble.className = "message-bubble assistant loading-dots";
      bubble.textContent = sanitizeDisplayText(text);
      row.appendChild(bubble);
      chatHistory.appendChild(row);
      scrollToBottom();
      return row;
    }

    function appendThinkingPlaceholder(text = "思考中") {
      removeEmptyState();
      const row = document.createElement("article");
      row.className = "message-row assistant";
      const bubble = document.createElement("div");
      bubble.className = "message-bubble thinking";
      bubble.textContent = sanitizeDisplayText(text);
      row.appendChild(bubble);
      chatHistory.appendChild(row);
      scrollToBottom();
      return row;
    }

    function replaceWithAnswer(row, data) {
      const next = document.createElement("article");
      next.className = "message-row assistant";
      const bubble = document.createElement("div");
      bubble.className = "message-bubble assistant";
      bubble.textContent = sanitizeDisplayText(stripCitationMarkers(stripMarkdownFormatting(data.answer || "")));
      appendAnswerFooter(bubble, data);
      next.appendChild(bubble);
      row.replaceWith(next);
      scrollToBottom();
    }

    function replaceWithSystemMessage(row, text) {
      const next = document.createElement("article");
      next.className = "message-row assistant";
      const bubble = document.createElement("div");
      bubble.className = "message-bubble assistant";
      bubble.textContent = sanitizeDisplayText(text);
      next.appendChild(bubble);
      row.replaceWith(next);
      scrollToBottom();
    }

    function replaceWithSecurityResult(row, data) {
      const next = document.createElement("article");
      next.className = "message-row assistant";
      const bubble = document.createElement("div");
      bubble.className = "message-bubble assistant";
      bubble.textContent = sanitizeDisplayText(formatSecurityResult(data));
      next.appendChild(bubble);
      row.replaceWith(next);
      scrollToBottom();
    }

    function replaceWithDiagnostics(row, data) {
      const next = document.createElement("article");
      next.className = "message-row search";
      const bubble = document.createElement("div");
      bubble.className = "message-bubble search";
      const label = document.createElement("div");
      label.className = "message-label";
      const results = Array.isArray(data.results) ? data.results : [];
      const totalCount = Number(data.total_count) || 0;
      label.textContent = "Diagnostics";
      bubble.appendChild(label);

      const meta = document.createElement("div");
      meta.className = "meta";
      const quality = totalCount
        ? "検索前段: 上位チャンクあり。Askがズレる場合は候補チャンクかLLM生成を確認。"
        : "検索前段: ヒットなし。filter、Reindex、検索語を確認。";
      meta.textContent = sanitizeDisplayText([
        `検索ヒット: ${totalCount}件`,
        formatFilterLine(data),
        quality
      ].join("\\n"));
      bubble.appendChild(meta);

      if (results.length) {
        const listLabel = document.createElement("div");
        listLabel.className = "message-label";
        listLabel.textContent = "上位チャンク";
        bubble.appendChild(listLabel);
        const list = document.createElement("div");
        list.className = "results-list";
        for (const item of results.slice(0, 5)) {
          list.appendChild(renderDiagnosticItem(item));
        }
        if (totalCount > 5) {
          const more = document.createElement("div");
          more.className = "meta";
          more.textContent = `他 ${totalCount - 5} 件`;
          list.appendChild(more);
        }
        bubble.appendChild(list);
      }
      next.appendChild(bubble);
      row.replaceWith(next);
      scrollToBottom();
    }

    function renderDiagnosticItem(item) {
      const el = document.createElement("div");
      el.className = "result-item";
      const title = document.createElement("div");
      title.className = "result-title";
      title.textContent = sanitizeDisplayText(item.title || item.relative_path || "untitled");
      const meta = document.createElement("div");
      meta.className = "meta";
      const scoreNumber = Number(item.score);
      const score = Number.isFinite(scoreNumber) ? scoreNumber.toFixed(2) : "";
      const parts = [
        item.relative_path,
        item.heading,
        item.chunk_index !== undefined ? `chunk ${item.chunk_index}` : "",
        item.match_source,
        score ? `score ${score}` : ""
      ].filter(Boolean);
      meta.textContent = sanitizeDisplayText(parts.join(" / "));
      el.append(title, meta);
      return el;
    }

    function replaceWithError(row, error) {
      const next = document.createElement("article");
      next.className = "message-row error";
      const bubble = document.createElement("div");
      bubble.className = "message-bubble error";
      bubble.textContent = safeErrorMessage(error);
      next.appendChild(bubble);
      row.replaceWith(next);
      scrollToBottom();
    }

    function appendAnswerFooter(parent, data) {
      const items = Array.isArray(data.citations) ? data.citations : [];
      const footer = document.createElement("div");
      footer.className = "answer-footer";
      const filterLine = document.createElement("div");
      filterLine.className = "answer-footer-line";
      filterLine.textContent = formatFilterLine(data);
      const sourceLine = document.createElement("div");
      sourceLine.className = "answer-footer-line";
      sourceLine.textContent = sourceCountText(items.length, data);
      footer.appendChild(filterLine);
      footer.appendChild(sourceLine);
      if (items.length) {
        footer.appendChild(renderSourceDetails(items));
      }
      parent.appendChild(footer);
    }

    function renderSourceDetails(items) {
      const details = document.createElement("details");
      details.className = "source-details";
      const summary = document.createElement("summary");
      summary.textContent = "Sources";
      details.appendChild(summary);
      const list = document.createElement("div");
      list.className = "results-list";
      for (const item of groupCitationItems(items)) {
        list.appendChild(renderCitationItem(item));
      }
      details.appendChild(list);
      return details;
    }

    function sourceCountText(count, data = null) {
      const returned = Number(data && data.citations_returned_count);
      const matched = Number(data && data.citations_matched_count);
      if (data && data.citations_limited && Number.isFinite(returned) && Number.isFinite(matched)) {
        return `Sources: ${returned} shown / ${matched} matched`;
      }
      const safeCount = Number.isFinite(returned) ? returned : count;
      return safeCount === 1 ? "Source: 1 item" : `Sources: ${safeCount} items`;
    }

    function groupCitationItems(items) {
      const seen = new Set();
      const deduped = [];
      for (const item of items) {
        const displayName = sourceFileName(item);
        const copyName = sourceCopyFileName(item);
        const key = copyName || displayName;
        if (seen.has(key)) continue;
        seen.add(key);
        deduped.push({ ...item, displayName, copyName });
      }
      return deduped;
    }

    function renderCitationItem(item) {
      const el = document.createElement("div");
      el.className = "citation-item";
      const header = document.createElement("div");
      header.className = "citation-header";
      const title = document.createElement("div");
      title.className = "citation-title";
      title.textContent = item.displayName || sourceFileName(item);
      const copyButton = document.createElement("button");
      copyButton.type = "button";
      copyButton.className = "copy-source";
      copyButton.title = "Copy filename";
      copyButton.setAttribute("aria-label", "Copy filename");
      copyButton.appendChild(copyIconSvg());
      copyButton.addEventListener("click", () => copySourceName(item.copyName || sourceCopyFileName(item), copyButton));
      header.append(title, copyButton);
      el.appendChild(header);
      return el;
    }

    function sourceFileName(item) {
      const rawPath = sanitizeDisplayText(item.relative_path || "");
      const name = rawPath.split(/[\\\\/]/).filter(Boolean).pop();
      return name || sanitizeDisplayText(item.title || "untitled");
    }

    function sourceCopyFileName(item) {
      return sourceFileName(item).replace(/\\.(?:md|markdown)$/i, "");
    }

    async function copySourceName(value, button) {
      const text = sanitizeDisplayText(value);
      if (!text) return;
      const previousLabel = button.getAttribute("aria-label") || "Copy filename";
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
        } else {
          fallbackCopyText(text);
        }
        button.classList.add("copied");
        button.setAttribute("aria-label", "Copied");
      } catch {
        button.setAttribute("aria-label", "Copy failed");
      } finally {
        window.setTimeout(() => {
          button.classList.remove("copied");
          button.setAttribute("aria-label", previousLabel);
        }, 900);
      }
    }

    function copyIconSvg() {
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("class", "icon-svg");
      svg.setAttribute("aria-hidden", "true");
      svg.setAttribute("viewBox", "0 0 24 24");
      const back = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      back.setAttribute("x", "9");
      back.setAttribute("y", "3");
      back.setAttribute("width", "11");
      back.setAttribute("height", "11");
      back.setAttribute("rx", "2");
      const front = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      front.setAttribute("x", "4");
      front.setAttribute("y", "8");
      front.setAttribute("width", "11");
      front.setAttribute("height", "11");
      front.setAttribute("rx", "2");
      svg.append(back, front);
      return svg;
    }

    function fallbackCopyText(text) {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.left = "-9999px";
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }

    function buildFilters() {
      const filters = {};
      const preset = filtersState.preset;
      const today = startOfToday();
      if (preset === "all_time") {
        filters.all_time = true;
      } else if (preset === "custom") {
        if (filtersState.dateFrom) filters.date_from = filtersState.dateFrom;
        if (filtersState.dateTo) filters.date_to = filtersState.dateTo;
      } else if (preset === "today") {
        const value = formatDate(today);
        filters.date_from = value;
        filters.date_to = value;
      } else if (preset === "yesterday") {
        const value = formatDate(addDays(today, -1));
        filters.date_from = value;
        filters.date_to = value;
      } else {
        const days = preset === "last_7" ? 7 : preset === "last_90" ? 90 : 30;
        let from = addDays(today, -(days - 1));
        if (preset === "this_month") from = new Date(today.getFullYear(), today.getMonth(), 1);
        if (preset === "this_year") from = new Date(today.getFullYear(), 0, 1);
        filters.date_from = formatDate(from);
        filters.date_to = formatDate(today);
      }

      const tags = splitList(filtersState.tags);
      const sourceNames = splitList(filtersState.sourceNames);
      if (tags.length) filters.tags = tags;
      if (sourceNames.length) filters.source_names = sourceNames;
      return filters;
    }

    function loadFilters() {
      try {
        const raw = JSON.parse(localStorage.getItem(FILTER_STORAGE_KEY) || "null");
        if (!raw || typeof raw !== "object") return { ...DEFAULT_FILTERS };
        return normalizeFilterState(raw);
      } catch {
        return { ...DEFAULT_FILTERS };
      }
    }

    function readFilterDraft() {
      return normalizeFilterState({
        preset: presetInput.value,
        dateFrom: dateFromInput.value,
        dateTo: dateToInput.value,
        tags: tagsInput.value,
        sourceNames: sourceNamesInput.value
      });
    }

    function normalizeFilterState(raw) {
      const preset = Object.prototype.hasOwnProperty.call(PRESET_LABELS, raw.preset) ? raw.preset : DEFAULT_FILTERS.preset;
      return {
        preset,
        dateFrom: cleanDate(raw.dateFrom),
        dateTo: cleanDate(raw.dateTo),
        tags: cleanInlineText(raw.tags),
        sourceNames: cleanInlineText(raw.sourceNames)
      };
    }

    function writeFilterDraft(filters) {
      presetInput.value = filters.preset;
      dateFromInput.value = filters.dateFrom;
      dateToInput.value = filters.dateTo;
      tagsInput.value = filters.tags;
      sourceNamesInput.value = filters.sourceNames;
      syncPreset();
    }

    function renderFilterSummary() {
      periodButtonText.textContent = sanitizeDisplayText(currentPeriodLabel());
      syncPeriodMenu();
    }

    function currentPeriodLabel() {
      return PRESET_LABELS[filtersState.preset] || PRESET_LABELS.last_30;
    }

    function syncPeriodMenu() {
      for (const option of periodMenu.querySelectorAll("[data-period]")) {
        option.classList.toggle("active", option.dataset.period === filtersState.preset);
      }
    }

    function formatFilterLine(data) {
      return `Period: ${formatFilterValue(data) || "none"}`;
    }

    function formatFilterValue(data) {
      const filters = data.applied_filters || {};
      const parts = [];
      if (filters.all_time) parts.push("all time");
      if (filters.date_from || filters.date_to) parts.push(`${filters.date_from || "未指定"} - ${filters.date_to || "未指定"}`);
      if (Array.isArray(filters.tags) && filters.tags.length) parts.push(`tags: ${filters.tags.join(", ")}`);
      if (Array.isArray(filters.source_names) && filters.source_names.length) parts.push(`sources: ${filters.source_names.join(", ")}`);
      if (!parts.length) return "";
      return sanitizeDisplayText(parts.join(" / "));
    }

    function formatReindexResult(data) {
      const warnings = Array.isArray(data.warnings) ? data.warnings.map(sanitizeDisplayText) : [];
      const warningText = warnings.length ? ` / warnings: ${warnings.length}` : "";
      const details = warnings.length ? `\\n${warnings.slice(0, 3).join("\\n")}` : "";
      return `Reindex完了: documents ${data.documents || 0} / chunks ${data.chunks || 0}${warningText}${details}`;
    }

    function formatSecurityResult(data) {
      const results = Array.isArray(data.results) ? data.results : [];
      const failCount = Number(data.fail_count) || 0;
      const warnCount = Number(data.warn_count) || 0;
      const skippedCount = Number(data.skipped_count) || 0;
      const lines = [securitySummaryText(failCount, warnCount, skippedCount, results), "", "詳細:"];
      for (const item of results) {
        const status = securityStatusLabel(item.status);
        const name = item.name || "check";
        const summary = item.summary || "";
        lines.push(`${status}: ${name} - ${summary}`);
        if ((item.status === "fail" || item.status === "warn") && item.details) {
          lines.push(truncate(String(item.details), 420));
        }
      }
      return lines.join("\\n");
    }

    function securitySummaryText(failCount, warnCount, skippedCount, results) {
      const lines = [
        `セキュリティチェックの結果: 失敗 ${failCount}件 / 警告 ${warnCount}件 / 未実行 ${skippedCount}件。`
      ];
      if (failCount > 0) {
        lines.push("失敗した項目があります。詳細の「失敗」を優先して確認してください。");
      } else if (warnCount || skippedCount) {
        lines.push("重大な失敗はありません。警告または未実行の項目だけ確認してください。");
      } else {
        lines.push("すべての項目が合格しました。");
      }

      const gitWarn = results.find(item => item.status === "warn" && item.name === "git status");
      if (gitWarn) {
        lines.push("警告の主因は未コミットの変更です。作業中なら想定内で、commit後に消えます。");
      }
      const gitleaksSkipped = results.find(item => item.status === "skipped" && item.name === "gitleaks");
      if (gitleaksSkipped) {
        lines.push("gitleaksはサーバーのPATHにないため未実行です。履歴secret検査まで含めるならgitleaksをPATHに追加してください。");
      }
      return lines.join("\\n");
    }

    function securityStatusLabel(status) {
      if (status === "pass") return "合格";
      if (status === "warn") return "警告";
      if (status === "fail") return "失敗";
      if (status === "skipped") return "未実行";
      return "不明";
    }

    function syncPreset() {
      const custom = presetInput.value === "custom";
      dateFromField.hidden = !custom;
      dateToField.hidden = !custom;
      dateFromInput.disabled = !custom;
      dateToInput.disabled = !custom;
      if (!custom) {
        dateFromInput.value = "";
        dateToInput.value = "";
      }
    }

    async function saveToken() {
      const candidate = tokenInput.value.trim();
      clearTokenError();
      if (!candidate) {
        showTokenError(INVALID_TOKEN_MESSAGE);
        tokenInput.focus();
        return;
      }
      setTokenSavePending(true);
      try {
        await validateToken(candidate);
        sessionStorage.setItem(TOKEN_STORAGE_KEY, candidate);
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        tokenInput.value = candidate;
        statusLine.textContent = "token saved for session";
        closeTokenDialog();
        maybeStartInitialReindex();
      } catch (error) {
        showTokenError(error && error.message ? error.message : INVALID_TOKEN_MESSAGE);
        tokenInput.focus();
        tokenInput.select();
      } finally {
        setTokenSavePending(false);
      }
    }

    async function validateToken(candidate) {
      let response;
      try {
        response = await fetch(API_PATHS.health, { method: "GET", headers: headers(candidate) });
      } catch {
        throw new Error("Token validation failed.");
      }
      if (response.status === 401) {
        throw new Error(INVALID_TOKEN_MESSAGE);
      }
      if (!response.ok) {
        throw new Error(messageForStatus(response.status, {}));
      }
    }

    function handleAuthFailure() {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      tokenInput.value = "";
      initialReindexPending = true;
      initialReindexStarted = false;
      showTokenError(INVALID_TOKEN_MESSAGE);
      openTokenDialog();
    }

    function showTokenError(message) {
      tokenError.textContent = sanitizeDisplayText(message);
      tokenError.hidden = false;
      statusLine.textContent = message;
    }

    function clearTokenError() {
      tokenError.textContent = "";
      tokenError.hidden = true;
    }

    function setTokenSavePending(pending) {
      saveTokenButton.disabled = pending;
    }

    function loadToken() {
      const sessionToken = sessionStorage.getItem(TOKEN_STORAGE_KEY) || "";
      const legacyToken = localStorage.getItem(TOKEN_STORAGE_KEY) || "";
      if (legacyToken) {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        if (!sessionToken) {
          sessionStorage.setItem(TOKEN_STORAGE_KEY, legacyToken);
          return legacyToken;
        }
      }
      return sessionToken;
    }

    function openTokenDialog() {
      tokenOverlay.hidden = false;
      tokenDialog.hidden = false;
      tokenInput.focus();
    }

    function closeTokenDialog() {
      if (!tokenInput.value.trim()) return;
      clearTokenError();
      tokenOverlay.hidden = true;
      tokenDialog.hidden = true;
    }

    function updateCommandMenu() {
      const value = chatInput.value.trimStart();
      if (busy || !value.startsWith("/")) {
        closeCommandMenu();
        return;
      }
      if (/^[/]\\S+\\s/.test(value)) {
        closeCommandMenu();
        return;
      }
      const typed = value.split(/\\s+/, 1)[0].toLowerCase();
      const matches = COMMANDS.filter(command => command.name.startsWith(typed));
      if (!matches.length) {
        closeCommandMenu();
        return;
      }
      commandMenu.replaceChildren();
      for (const command of matches) {
        const option = document.createElement("div");
        option.className = "command-option";
        option.role = "option";
        option.tabIndex = -1;
        option.dataset.command = command.name;
        const name = document.createElement("span");
        name.className = "command-name";
        name.textContent = command.name;
        option.appendChild(name);
        commandMenu.appendChild(option);
      }
      commandMenu.hidden = false;
    }

    function closeCommandMenu() {
      commandMenu.hidden = true;
    }

    function selectCommand(name) {
      const command = COMMANDS.find(item => item.name === name);
      if (!command) return;
      chatInput.value = command.insertText;
      autoResizeInput();
      updateSendState();
      closeCommandMenu();
      chatInput.focus();
    }

    function togglePeriodMenu() {
      if (periodMenu.hidden) {
        openPeriodMenu();
      } else {
        closePeriodMenu();
      }
    }

    function openPeriodMenu() {
      closeCommandMenu();
      syncPeriodMenu();
      periodOverlay.hidden = false;
      periodMenu.hidden = false;
      updateViewportLayout();
    }

    function closePeriodMenu() {
      periodOverlay.hidden = true;
      periodMenu.hidden = true;
    }

    function selectPeriod(preset) {
      if (!Object.prototype.hasOwnProperty.call(PRESET_LABELS, preset)) return;
      filtersState = normalizeFilterState({ ...filtersState, preset });
      localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(filtersState));
      writeFilterDraft(filtersState);
      renderFilterSummary();
      closePeriodMenu();
      if (preset === "custom") {
        openFilterPanel();
        dateFromInput.focus();
        if (typeof dateFromInput.showPicker === "function") {
          try { dateFromInput.showPicker(); } catch {}
        }
      }
    }

    function openFilterPanel() {
      closeCommandMenu();
      closePeriodMenu();
      writeFilterDraft(filtersState);
      filterStatus.textContent = "";
      filterOverlay.hidden = false;
      filterPanel.hidden = false;
      updateViewportLayout();
    }

    function closeFilterPanel() {
      filtersState = readFilterDraft();
      localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(filtersState));
      renderFilterSummary();
      filterOverlay.hidden = true;
      filterPanel.hidden = true;
    }

    function dismissKeyboardFromChatHistory(event) {
      if (document.activeElement !== chatInput) return;
      if (event.pointerType && event.pointerType !== "touch" && event.pointerType !== "pen") return;
      chatInput.blur();
      closeCommandMenu();
      updateViewportLayout();
    }

    function setBusy(nextBusy) {
      busy = nextBusy;
      chatInput.disabled = nextBusy;
      sendButton.disabled = nextBusy;
      filterButton.disabled = nextBusy;
      sendButton.textContent = "↑";
      sendButton.classList.toggle("ready", false);
      statusLine.textContent = nextBusy ? "asking" : statusLine.textContent;
      if (nextBusy) closeCommandMenu();
      if (!nextBusy) updateSendState();
    }

    function updateSendState() {
      const hasText = chatInput.value.trim().length > 0;
      sendButton.disabled = busy || !hasText;
      sendButton.classList.toggle("ready", hasText && !busy);
      if (!busy) updateCommandMenu();
    }

    function safeErrorMessage(error) {
      let text = String(error && error.message ? error.message : error);
      if (/Failed to fetch|NetworkError|Load failed/i.test(text)) {
        text = "接続できません。起動状態を確認してください。";
      }
      return sanitizeDisplayText(text) || "エラーが発生しました。";
    }

    function sanitizeDisplayText(value) {
      let text = cleanAnswer(String(value ?? ""));
      const token = tokenInput.value.trim();
      if (token) text = text.split(token).join("[redacted]");
      const pathPatterns = [
        new RegExp("/" + "Users" + "/[^\\\\s\\\"'<>]+", "g"),
        new RegExp("/" + "private" + "/[^\\\\s\\\"'<>]+", "g"),
        new RegExp("[A-Za-z]:\\\\\\\\[^\\\\s\\\"'<>]+", "g")
      ];
      for (const pattern of pathPatterns) {
        text = text.replace(pattern, "[local path]");
      }
      return text.trim();
    }

    function cleanAnswer(text) {
      const hiddenTag = "thi" + "nk";
      const thinkingPrefix = "Thin" + "king";
      return String(text)
        .replace(new RegExp("<" + hiddenTag + ">[\\\\s\\\\S]*?</" + hiddenTag + ">", "gi"), "")
        .replace(new RegExp("^\\\\s*" + thinkingPrefix + "\\\\.\\\\.\\\\.\\\\s*", "i"), "")
        .trim();
    }

    function stripCitationMarkers(text) {
      return String(text)
        .replace(/\\s*\\[(?:\\d+)(?:\\s*,\\s*\\d+)*(?:-\\d+)?\\]/g, "")
        .replace(/[ \\t]{2,}/g, " ")
        .replace(/\\s+([。！？、,.!?])/g, "$1")
        .trim();
    }

    function stripMarkdownFormatting(text) {
      return String(text)
        .replace(/^[ \\t]*(```|~~~).*$/gm, "")
        .replace(/^[ \\t]*\\|?[ \\t]*:?-{3,}:?[ \\t]*(?:\\|[ \\t]*:?-{3,}:?[ \\t]*)+\\|?[ \\t]*$/gm, "")
        .replace(/^[ \\t]*(?:-{3,}|\\*{3,}|_{3,})[ \\t]*$/gm, "")
        .replace(/^[ \\t]{0,3}#{1,6}[ \\t]*/gm, "")
        .replace(/^[ \\t]{0,3}>[ \\t]?/gm, "")
        .replace(/^[ \\t]*[-*+][ \\t]+/gm, "")
        .replace(/^([ \\t]*)(\\d+)[.)][ \\t]+/gm, "$1$2. ")
        .replace(/(\\*\\*|__)([^\\n]+?)\\1/g, "$2")
        .replace(/(^|[^*])\\*([^*\\n]+?)\\*(?!\\*)/g, "$1$2")
        .replace(/(^|\\W)_([^_\\n]+?)_(?=\\W|$)/g, "$1$2")
        .replace(/`([^`\\n]+?)`/g, "$1")
        .replace(/`/g, "")
        .replace(/[ \\t]+$/gm, "")
        .replace(/\\n{3,}/g, "\\n\\n")
        .trim();
    }

    function cleanDate(value) {
      const text = cleanInlineText(value);
      return /^\\d{4}-\\d{2}-\\d{2}$/.test(text) ? text : "";
    }

    function cleanInlineText(value) {
      return sanitizeDisplayText(value).replace(/[\\r\\n]+/g, " ").trim();
    }

    function splitList(value) {
      return cleanInlineText(value).split(/[\\s,]+/).map(item => item.trim()).filter(Boolean);
    }

    function truncate(text, maxLength) {
      return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
    }

    function startOfToday() {
      const now = new Date();
      return new Date(now.getFullYear(), now.getMonth(), now.getDate());
    }

    function addDays(date, days) {
      const copy = new Date(date.getTime());
      copy.setDate(copy.getDate() + days);
      return copy;
    }

    function formatDate(date) {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    }

    function autoResizeInput() {
      chatInput.style.height = "auto";
      chatInput.style.height = `${Math.min(chatInput.scrollHeight, 132)}px`;
      updateViewportLayout();
    }

    function updateViewportLayout() {
      updateComposerHeight();
      const viewport = window.visualViewport;
      let keyboardOffset = 0;
      if (viewport) {
        keyboardOffset = Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop);
      }
      document.documentElement.style.setProperty("--keyboard-offset", `${Math.ceil(keyboardOffset)}px`);
      if (document.activeElement === chatInput) scrollToBottom();
    }

    function updateComposerHeight() {
      if (!composerWrap) return;
      const height = Math.ceil(composerWrap.getBoundingClientRect().height);
      document.documentElement.style.setProperty("--composer-height", `${height}px`);
    }

    function removeEmptyState() {
      if (emptyState && emptyState.parentNode) emptyState.remove();
    }

    function scrollToBottom() {
      requestAnimationFrame(() => {
        chatHistory.scrollTo({ top: chatHistory.scrollHeight, behavior: "smooth" });
      });
    }
  </script>
</body>
</html>"""


DEV_SECURITY_API_PATH_JS = ',\n      security: "/security/check"'
DEV_SECURITY_COMMAND_JS = ',\n      { name: "/security", insertText: "/security" }'
DEV_SECURITY_HANDLER_JS = """      if (rawText.toLowerCase().startsWith("/security")) {
        closeCommandMenu();
        const match = rawText.toLowerCase().match(/^[/]security$/);
        appendUserMessage(rawText);
        chatInput.value = "";
        autoResizeInput();
        updateSendState();
        const row = appendThinkingPlaceholder("Security診断中");
        setBusy(true);
        try {
          if (!match) throw new Error("使い方: /security");
          const profile = "full";
          const data = await postJson(API_PATHS.security, { profile });
          replaceWithSecurityResult(row, data);
        } catch (error) {
          replaceWithError(row, error);
        } finally {
          setBusy(false);
          chatInput.focus();
        }
        return;
      }
"""


def render_index_html(enable_dev_security: bool = False) -> str:
    return (
        INDEX_HTML_TEMPLATE.replace(
            "__DEV_SECURITY_API_PATH__",
            DEV_SECURITY_API_PATH_JS if enable_dev_security else "",
        )
        .replace(
            "__DEV_SECURITY_COMMAND__",
            DEV_SECURITY_COMMAND_JS if enable_dev_security else "",
        )
        .replace(
            "__DEV_SECURITY_HANDLER__",
            DEV_SECURITY_HANDLER_JS if enable_dev_security else "",
        )
    )


INDEX_HTML = render_index_html(False)

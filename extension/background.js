// Clara accessibility overlay — service worker.
//
// The overlay approach: LLM web UIs (ChatGPT, Claude, Gemini) don't let you
// change their backend, so Clara sits on top instead — select any text on any
// page, right-click, "Simplify with Clara". The selection goes to your Clara
// server (/simplify), and the simplified text comes back in an accessible
// overlay with read-aloud and the faithfulness verdict. Works on every website,
// not only chat UIs: letters, government pages, news.
//
// Privacy: the selected text is sent ONLY to the Clara server configured in the
// options (localhost by default — nothing leaves the machine).

const DEFAULTS = { server: "http://localhost:8000", lang: "auto", level: "plain" };
const LANGS = ["en", "ru", "es", "de", "fr"];

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "clara-simplify",
    title: chrome.i18n.getMessage("menu_simplify"),
    contexts: ["selection"],
  });
});

async function getSettings() {
  const stored = await chrome.storage.sync.get(DEFAULTS);
  return { ...DEFAULTS, ...stored };
}

function resolveLang(setting) {
  if (setting && setting !== "auto") return setting;
  const ui = (chrome.i18n.getUILanguage() || "en").slice(0, 2).toLowerCase();
  return LANGS.includes(ui) ? ui : "en";
}

function labels() {
  const m = (k) => chrome.i18n.getMessage(k);
  return { title: m("overlay_title"), warn: m("overlay_warning"),
           speak: m("overlay_speak"), close: m("overlay_close") };
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "clara-simplify" || !info.selectionText || !tab || !tab.id) return;
  const s = await getSettings();
  const lang = resolveLang(s.lang);
  let payload;
  try {
    const r = await fetch(`${s.server.replace(/\/+$/, "")}/simplify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: info.selectionText, level: s.level, lang }),
    });
    const d = await r.json();
    if (!r.ok || d.error) throw new Error(d.error || `HTTP ${r.status}`);
    payload = {
      ok: true,
      text: d.simplified || "",
      faithful: d.faithfulness ? d.faithfulness.ok : null,
      lang,
      labels: labels(),
    };
  } catch (e) {
    payload = {
      ok: false,
      text: `${chrome.i18n.getMessage("overlay_error")}\n${e.message}`,
      faithful: null,
      lang,
      labels: labels(),
    };
  }
  chrome.scripting.executeScript({ target: { tabId: tab.id }, func: showOverlay, args: [payload] });
});

// Injected into the page on demand (activeTab) — self-contained: builds an
// accessible dialog, offers read-aloud, and cleans up after itself.
function showOverlay(p) {
  const OLD = document.getElementById("clara-a11y-overlay");
  if (OLD) OLD.remove();

  const BCP47 = { en: "en-US", ru: "ru-RU", es: "es-ES", de: "de-DE", fr: "fr-FR" };
  const box = document.createElement("div");
  box.id = "clara-a11y-overlay";
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-label", p.labels.title);
  box.style.cssText =
    "position:fixed;top:16px;right:16px;z-index:2147483647;max-width:440px;" +
    "background:#ffffff;color:#1a1a1a;border:2px solid #0f7d74;border-radius:12px;" +
    "box-shadow:0 8px 30px rgba(0,0,0,.25);padding:16px 18px;" +
    "font:18px/1.6 system-ui,sans-serif;";

  const head = document.createElement("div");
  head.style.cssText = "display:flex;align-items:center;gap:8px;margin-bottom:8px;";
  const title = document.createElement("strong");
  title.textContent = p.labels.title;
  title.style.cssText = "flex:1;font-size:15px;color:#0f7d74;";

  const speakBtn = document.createElement("button");
  speakBtn.type = "button";
  speakBtn.textContent = "🔊 " + p.labels.speak;
  speakBtn.setAttribute("aria-label", p.labels.speak);
  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.textContent = "✕";
  closeBtn.setAttribute("aria-label", p.labels.close);
  for (const b of [speakBtn, closeBtn]) {
    b.style.cssText =
      "border:1px solid #cbd2d9;background:#f6f7f9;color:#1a1a1a;border-radius:8px;" +
      "padding:4px 10px;font:inherit;font-size:14px;cursor:pointer;";
  }

  const body = document.createElement("div");
  body.textContent = p.text;
  body.lang = p.lang || "";
  body.style.cssText = "white-space:pre-wrap;max-height:50vh;overflow:auto;";

  head.append(title, speakBtn, closeBtn);
  box.append(head, body);

  if (p.faithful === false) {
    const warn = document.createElement("p");
    warn.textContent = "⚠ " + p.labels.warn;
    warn.style.cssText =
      "margin:10px 0 0;padding:8px 10px;border:1px solid #9a6700;border-radius:8px;" +
      "background:#fff5e0;color:#9a6700;font-size:15px;";
    box.append(warn);
  }

  function close() {
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    box.remove();
    document.removeEventListener("keydown", onKey);
  }
  function onKey(e) { if (e.key === "Escape") close(); }

  speakBtn.onclick = () => {
    if (!("speechSynthesis" in window)) return;
    if (speechSynthesis.speaking) { speechSynthesis.cancel(); return; }
    const u = new SpeechSynthesisUtterance(p.text);
    u.lang = BCP47[p.lang] || p.lang || "";
    speechSynthesis.speak(u);
  };
  closeBtn.onclick = close;
  document.addEventListener("keydown", onKey);

  document.documentElement.append(box);
  closeBtn.focus();
}

// Clara popup — paste text, simplify via your Clara server, listen to the result.

const DEFAULTS = { server: "http://localhost:8000", lang: "auto", level: "plain" };
const LANGS = ["en", "ru", "es", "de", "fr"];
const BCP47 = { en: "en-US", ru: "ru-RU", es: "es-ES", de: "de-DE", fr: "fr-FR" };

const $ = (id) => document.getElementById(id);
const msg = (k) => chrome.i18n.getMessage(k);

$("lbl").textContent = msg("popup_label");
$("go").textContent = msg("popup_simplify");
$("speak").setAttribute("aria-label", msg("overlay_speak"));
$("speak").title = msg("overlay_speak");
$("opts").textContent = msg("popup_options");
$("opts").onclick = (e) => { e.preventDefault(); chrome.runtime.openOptionsPage(); };

function resolveLang(setting) {
  if (setting && setting !== "auto") return setting;
  const ui = (chrome.i18n.getUILanguage() || "en").slice(0, 2).toLowerCase();
  return LANGS.includes(ui) ? ui : "en";
}

let lastText = "";
let lastLang = "en";

$("go").onclick = async () => {
  const text = $("text").value.trim();
  if (!text) return;
  $("go").disabled = true;
  try {
    const s = { ...DEFAULTS, ...(await chrome.storage.sync.get(DEFAULTS)) };
    const lang = resolveLang(s.lang);
    const r = await fetch(`${s.server.replace(/\/+$/, "")}/simplify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, level: s.level, lang }),
    });
    const d = await r.json();
    if (!r.ok || d.error) throw new Error(d.error || `HTTP ${r.status}`);
    lastText = d.simplified || "";
    lastLang = lang;
    $("result").textContent = lastText;
    $("result").lang = lang;
    $("result").style.display = "block";
    const bad = d.faithfulness && d.faithfulness.ok === false;
    $("warn").textContent = bad ? "⚠ " + msg("overlay_warning") : "";
    $("warn").style.display = bad ? "block" : "none";
  } catch (e) {
    $("result").textContent = `${msg("overlay_error")}\n${e.message}`;
    $("result").style.display = "block";
    $("warn").style.display = "none";
  } finally {
    $("go").disabled = false;
  }
};

$("speak").onclick = () => {
  if (!("speechSynthesis" in window) || !lastText) return;
  if (speechSynthesis.speaking) { speechSynthesis.cancel(); return; }
  const u = new SpeechSynthesisUtterance(lastText);
  u.lang = BCP47[lastLang] || lastLang;
  speechSynthesis.speak(u);
};

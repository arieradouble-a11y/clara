// Clara extension options: which Clara server to use, language, reading level.

const DEFAULTS = { server: "http://localhost:8000", lang: "auto", level: "plain" };
const $ = (id) => document.getElementById(id);
const msg = (k) => chrome.i18n.getMessage(k);

$("h").textContent = msg("ext_name");
$("lbl-server").textContent = msg("opt_server");
$("hint-server").textContent = msg("opt_server_hint");
$("lbl-lang").textContent = msg("opt_lang");
$("opt-auto").textContent = msg("opt_lang_auto");
$("lbl-level").textContent = msg("opt_level");
$("opt-plain").textContent = msg("opt_level_plain");
$("opt-easy").textContent = msg("opt_level_easy");
$("save").textContent = msg("opt_save");
$("saved").textContent = msg("opt_saved");

chrome.storage.sync.get(DEFAULTS).then((s) => {
  $("server").value = s.server || DEFAULTS.server;
  $("lang").value = s.lang || "auto";
  $("level").value = s.level || "plain";
});

$("save").onclick = async () => {
  let server = $("server").value.trim().replace(/\/+$/, "") || DEFAULTS.server;
  try {
    // A server outside the defaults needs an optional host permission grant.
    const origin = new URL(server).origin + "/*";
    const granted = await chrome.permissions.contains({ origins: [origin] });
    if (!granted) await chrome.permissions.request({ origins: [origin] });
  } catch (e) {
    // Invalid URL — keep whatever the user typed; the fetch will surface it.
  }
  await chrome.storage.sync.set({ server, lang: $("lang").value, level: $("level").value });
  $("saved").style.visibility = "visible";
  setTimeout(() => { $("saved").style.visibility = "hidden"; }, 1500);
};

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { runInNewContext } from "node:vm";
import { applianceName, applianceNames, applianceSelection, locale, messages, relativeTime, translate } from "../custom_components/empreinte/frontend/i18n.js";

assert.equal(applianceName("it", "Lave-linge"), "Lavatrice");
assert.equal(applianceName("en", "Lave-vaisselle"), "Dishwasher");
assert.equal(applianceName("fr", "Lave-linge"), "Lave-linge");
assert.equal(applianceName("it", "La mia lavatrice"), "La mia lavatrice");
assert.equal(applianceName("invalid", "Lave-linge"), "Lave-linge");
for (const [name, translations] of Object.entries(applianceNames)) {
  assert.equal(translations.length, 2, name);
  assert.ok(translations.every(Boolean), name);
}
const input = { value: "", handlers: {}, addEventListener(event, callback) { this.handlers[event] = callback; }, focus() {} };
const chip = { dataset: { s: "Lave-linge" } };
const selectedName = applianceSelection(input, [chip], "it", "Lave-vaisselle");
assert.equal(input.value, "Lavastoviglie");
assert.equal(selectedName(), "Lave-vaisselle");
chip.onclick();
assert.equal(input.value, "Lavatrice");
assert.equal(selectedName(), "Lave-linge");
input.value = "Lavatrice personale";
input.handlers.input();
assert.equal(selectedName(), "Lavatrice personale");

assert.equal(translate("fr", "overview"), "Aperçu");
assert.equal(translate("en", "overview"), "Overview");
assert.equal(translate("it", "overview"), "Panoramica");
assert.equal(translate("en", "today"), "Today");
assert.equal(translate("it", "today"), "Oggi");
assert.equal(translate("invalid", "overview"), "Aperçu");
assert.equal(locale("it"), "it-IT");
assert.equal(locale("en"), "en-GB");
assert.equal(locale("invalid"), "fr-FR");
for (const language of ["en", "it"]) {
  assert.deepEqual(Object.keys(messages[language]).sort(), Object.keys(messages.fr).sort());
  for (const [key, value] of Object.entries(messages[language])) {
    assert.ok(value, `Missing ${language} translation for ${key}`);
    const placeholders = text => [...text.matchAll(/\{(\w+)\}/g)].map(match => match[1]).sort();
    assert.deepEqual(placeholders(value), placeholders(messages.fr[key]), `Placeholder mismatch for ${language}.${key}`);
  }
  const app = await readFile(new URL("../custom_components/empreinte/frontend/app.js", import.meta.url), "utf8");
  for (const [, key] of app.matchAll(/\btr\("([^"]+)"\)/g)) {
    assert.ok(Object.hasOwn(messages.fr, key), `Missing translation key ${key}`);
  }
}
assert.equal(relativeTime("it", 1000, 1000), "adesso");
assert.equal(relativeTime("en", 1000, 1000), "just now");
assert.equal(relativeTime("fr", 1000, 1000), "à l'instant");
assert.equal(translate("it", "trackingLabel", { name: "Lavatrice <test>" }), "« Lavatrice <test> » monitorato fino allo spegnimento");
assert.equal(translate("en", "expectedAt", { time: "14:30" }), "Expected to finish at 14:30");
assert.equal(translate("en", "expectedAt"), "Expected to finish at {time}");
const source = await readFile(new URL("../custom_components/empreinte/frontend/app.js", import.meta.url), "utf8");
const settingsPage = source.slice(source.indexOf("function pageSettings()"), source.indexOf("// ---------- Rendu"));
for (const language of ["fr", "en", "it"]) {
  const button = { disabled: false }, result = { textContent: "" };
  const form = { querySelector: () => button };
  const fields = {
    "#settings-form": form,
    "#settings-language": { value: language },
    "#settings-threshold": { value: "75" },
    "#settings-result": result,
  };
  const sent = [];
  let renders = 0;
  const context = {
    S: { status: { detection_w: 75 } }, language,
    esc: String, tr: (key, values) => translate(context.language, key, values),
    $: selector => fields[selector],
    call: async msg => { assert.equal(button.disabled, true); sent.push(JSON.parse(JSON.stringify(msg))); },
    setLanguage: selected => { context.language = selected; },
    render: () => { renders++; },
  };
  runInNewContext(settingsPage, context);
  const page = context.pageSettings();
  assert.ok(page.includes(`value="${language}" selected`));
  assert.ok(page.includes('required value="75"'));
  for (const key of ["settings", "settingsLanguage", "settingsThreshold", "settingsHistoryWarning"]) {
    assert.ok(page.includes(translate(language, key)));
  }
  context.mountSettings();
  const submit = () => form.onsubmit({ preventDefault() {}, currentTarget: form });
  for (const value of ["", "9", "2001", "75.5", "invalid"]) {
    fields["#settings-threshold"].value = value;
    await submit();
    assert.equal(result.textContent, translate(language, "settingsInvalidThreshold"));
  }
  assert.equal(sent.length, 0);
  for (const value of ["10", "75", "2000"]) {
    fields["#settings-threshold"].value = value;
    await submit();
    assert.deepEqual(sent.at(-1), { type: "empreinte/settings", language, detection_w: Number(value) });
    assert.equal(context.S.status.detection_w, Number(value));
    assert.equal(result.textContent, translate(language, "settingsSaved"));
    assert.equal(button.disabled, false);
  }
  assert.equal(renders, 3);
  fields["#settings-language"].value = "it";
  await submit();
  assert.equal(context.language, "it");
  assert.equal(context.S.status.language, "it");
  assert.equal(result.textContent, translate("it", "settingsSaved"));
  context.call = async () => { throw new Error("Permission denied"); };
  await submit();
  assert.ok(result.textContent.includes("Permission denied"));
  assert.equal(button.disabled, false);
  for (const key of ["discoverDetect", "introDetectText"]) {
    const text = translate(language, key, { threshold: 75 });
    assert.ok(text.includes("75"));
    assert.ok(!text.includes("350"));
  }
}
const devicePage = source.slice(source.indexOf("function stateOf("), source.indexOf("// ---------- Page : Rapport"));
for (const language of ["fr", "en", "it"]) {
  const now = Date.now() / 1000;
  const group = { id: "g1", name: "Lave-linge", status: "valide", conf: 0.6, n_uses: 3, n_sure: 1, n_fixed: 1 };
  const context = {
    S: { groups: [group], status: { categories: [{ id: "c1", name: "Kitchen <test>", dash: false },
      { id: "menager", name: "Électroménager", dash: false }],
      energy_log: [
        { id: 1, t: now - 60, start: now - 120, end: now - 90, name: "Lave-linge", kwh: 1, in_dash: true },
        { id: 2, t: now - 700, name: "Lave-linge", kwh: 1, in_dash: true },
        { id: 3, t: now - 800, name: "Lave-linge", kwh: 1, removed: true, auto: true },
        { id: 4, t: now - 800, name: "Électroménager", target: ["cat", "menager"], kwh: 1, removed: true },
      ], shared: [] } },
    hass: null, NDAYS: 1, Date, Math,
    tr: (key, values) => translate(language, key, values),
    esc: value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])),
    appliance: name => applianceName(language, name),
    gname: g => applianceName(language, g.name),
    gstats: () => ({ kwhWeek: 1, m: [], last: null, n: 1, P: 50, conf: 0.6 }),
    members: () => [], dayOf: () => 0, dayStartMs: () => 0, dayLabel: () => "day",
    dfDay: { format: () => "day" }, fmtW: v => `${v} W`, fmtKwh: v => `${v} kWh`,
    fmtEur: v => `${v} €`, fmtWhen: () => "time", fmtHM: () => "12:00",
    icon: () => "", gicon: () => "", col: () => "red", catCol: () => "red", confBar: () => "",
  };
  const page = runInNewContext(`${devicePage}\npageAppareils()`, context);
  for (const key of ["energyLogTitle", "energyLogDescription", "energySensorMissing", "energyAutoRemoved",
    "energyRestore", "rename", "delete", "addEnergy"]) {
    assert.ok(page.includes(translate(language, key)), `${language}: missing ${key} on devices page`);
  }
  assert.ok(page.includes(translate(language, "energyRemovableIn", { minutes: 9 })));
  assert.ok(page.includes(translate(language, "energyNeedsUses", { count: 5 })));
  assert.ok(page.includes(translate(language, "energyConfidence", { confidence: 60, uses: 3, confirmed: 1,
    fixed: translate(language, "energyFixed", { count: 1 }) })));
  assert.ok(page.includes("Kitchen &lt;test&gt;"));
  assert.ok(page.includes(translate(language, "defaultCategory")));
  assert.ok(page.includes(applianceName(language, "Lave-linge")));
  if (language !== "fr") assert.ok(!page.includes("Électroménager"));
  group.energy_dash = true;
  const active = runInNewContext(`${devicePage}\npageAppareils()`, context);
  assert.ok(active.includes(translate(language, "energyVisible")));
  for (const status of ["valide", "nomme"]) {
    group.status = status;
    const controls = runInNewContext(`${devicePage}\npageAppareils()`, context);
    assert.ok(controls.includes('href="#/groupe/g1"'));
    assert.ok(controls.includes(translate(language, "viewUses")));
    assert.ok(controls.includes('data-delete-appliance="g1"'));
    assert.ok(controls.includes(translate(language, "deleteAppliance")));
    assert.equal(controls.includes('data-val="g1"'), status !== "valide");
  }
}
const deleteModal = source.slice(source.indexOf("function deleteApplianceModal("), source.indexOf("// ---------- Fenêtres"));
let confirmDelete, closed = false, deletion;
runInNewContext(`${deleteModal}\ndeleteApplianceModal("g1");`, {
  G: () => ({ name: "<Lamp>" }), gname: g => g.name,
  tr: (key, values) => translate("it", key, values),
  esc: text => text.replace(/</g, "&lt;").replace(/>/g, "&gt;"), icon: () => "",
  $: () => confirmDelete,
  openModal: (html, mount) => {
    assert.ok(html.includes("&lt;Lamp&gt;"));
    assert.ok(html.includes(translate("it", "deleteApplianceDescription")));
    confirmDelete = {};
    mount({}, () => { closed = true; });
  },
  act: msg => { deletion = JSON.parse(JSON.stringify(msg)); },
});
assert.equal(deletion, undefined);
confirmDelete.onclick();
assert.equal(closed, true);
assert.deepEqual(deletion, { action: "delete", gid: "g1" });
const reportPage = source.slice(source.indexOf("function reportDays()"), source.indexOf("function pageSettings()"));
for (const language of ["fr", "en", "it"]) {
  const groups = [
    { id: "new", status: "nouveau", letter: "A", created: Date.now() / 1000, hyp: "Lave-linge" },
    { id: "unknown", status: "nouveau", letter: "B", created: 0 },
    { id: "ready", status: "nomme", name: "Lave-linge", auto: true, conf: 0.9 },
    { id: "named", status: "nomme", name: "<Custom>", conf: 0.9 },
    { id: "valid", status: "valide", name: "Four" },
  ];
  const item = { gid: "valid", start: 0 };
  const cell = { dataset: { v: "1", l: "<day>" } };
  let tip = "";
  const ctx = {
    S: { groups, status: { verdicts: { n: 2, ok: 1, errors: [{ start: 1, auto: "Lave-linge", user: "<wrong>" }] } } },
    NDAYS: 1, STEP: 15, PRIX: 0.22033, Date, Math, Intl, language, locale,
    tr: (key, values) => translate(language, key, values),
    esc: value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])),
    dayData: () => ({ tot: 2, order: ["base", "valid"], kwh: { base: 1, valid: 1 }, hours: 24, limit: 1,
      layers: new Map([["base", [200]], ["valid", [1000]]]), evs: [item], ds: 0 }),
    dayStartMs: () => 0, dayLabel: () => "day", dfDay: { format: () => "day" },
    nf1: { format: x => String(x) }, nf0: { format: x => String(Math.round(x)) }, nf2: { format: x => String(x) },
    G: id => groups.find(g => g.id === id), members: id => id === "valid" ? [item] : [],
    isAty: () => true, gstats: id => ({ n: 3, P: 50, D: 60, conf: 0.9,
      split: id === "valid" ? { lowP: 50, highP: 100 } : null }),
    gname: g => applianceName(language, g.name || g.letter), appliance: name => applianceName(language, name),
    hypLabel: g => g.hyp, hypReasons: () => [], confBar: () => "", icon: () => "", col: () => "red",
    gicon: () => "", layerCol: () => "red", layerName: k => k, clamp: (x, a, b) => Math.max(a, Math.min(b, x)),
    fmtW: v => `${Math.round(v)} W`, fmtDur: v => `${v} s`, fmtKwh: v => `${v} kWh`,
    fmtEur: v => `${v} €`, fmtWhen: () => "time",
    mountOverlays: () => {}, $: () => ({}), $$: selector => selector === "#heat i[data-l]" ? [cell] : [],
    showTip: (_, html) => { tip = html; }, moveTip: () => {}, hideTip: () => {},
  };
  const page = runInNewContext(`${reportPage}\npageRapport()`, ctx);
  for (const key of ["reportPrint", "reportConsumption", "reportAttributed", "reportGroupsToConfirm",
    "reportFindings", "reportEnergyByGroup", "reportWhenConsuming", "reportHeatHelp", "reportChanges",
    "reportDetails", "reportLow", "reportHigh", "reportErrors", "looksGood", "noInstead"]) {
    assert.ok(page.includes(translate(language, key)), `${language}: missing ${key} on report page`);
  }
  assert.ok(page.includes(translate(language, "reportReliability", { correct: 1, total: 2 })));
  assert.ok(page.includes(translate(language, "reportGroupUnknown", { letter: "B" })));
  assert.ok(page.includes(translate(language, "reportGroupLooksLike", { letter: "A", name: applianceName(language, "Lave-linge") })));
  assert.ok(page.includes("&lt;Custom&gt;"));
  assert.ok(page.includes("&lt;wrong&gt;"));
  runInNewContext(`${reportPage}\nmountRapport()`, ctx);
  cell.onpointerenter({});
  assert.ok(tip.includes(translate(language, "reportConsumed")));
  assert.ok(tip.includes("&lt;day&gt;"));
  ctx.S.groups = [];
  ctx.S.status.verdicts = { n: 0, ok: 0, errors: [] };
  const empty = runInNewContext(`${reportPage}\npageRapport()`, ctx);
  assert.ok(empty.includes(translate(language, "reportReliabilityEmpty")));
  assert.ok(empty.includes(translate(language, "reportNoneReady")));
}
assert.ok(!source.includes('tr("partial")'));
const panel = await readFile(new URL("../custom_components/empreinte/frontend/empreinte-panel.js", import.meta.url), "utf8");
assert.ok(!panel.includes("language-notice"));
for (const language of ["fr", "en", "it"]) {
  for (const [seconds, amount, unit] of [[120, -2, "minute"], [7200, -2, "hour"], [172800, -2, "day"]]) {
    assert.equal(
      relativeTime(language, 0, seconds * 1000),
      new Intl.RelativeTimeFormat(locale(language), { numeric: "always", style: "short" }).format(amount, unit),
    );
  }
}
console.log("Localization tests passed");

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { locale, messages, relativeTime, translate } from "../custom_components/empreinte/frontend/i18n.js";

assert.equal(translate("fr", "overview"), "Aperçu");
assert.equal(translate("en", "overview"), "Overview");
assert.equal(translate("it", "overview"), "Panoramica");
assert.equal(translate("en", "today"), "Today");
assert.equal(translate("it", "today"), "Oggi");
assert.equal(translate("invalid", "overview"), "Aperçu");
assert.equal(locale("it"), "it-IT");
assert.equal(locale("en"), "en-GB");
assert.equal(locale("invalid"), "fr-FR");
assert.ok(translate("it", "partial"));
assert.equal(translate("fr", "partial"), "");
for (const language of ["en", "it"]) {
  assert.deepEqual(Object.keys(messages[language]).sort(), Object.keys(messages.fr).sort());
  for (const [key, value] of Object.entries(messages[language])) {
    assert.ok(value, `Missing ${language} translation for ${key}`);
  }
  const app = await readFile(new URL("../custom_components/empreinte/frontend/app.js", import.meta.url), "utf8");
  for (const [, key] of app.matchAll(/\btr\("([^"]+)"\)/g)) {
    assert.ok(Object.hasOwn(messages.fr, key), `Missing translation key ${key}`);
  }
}
assert.equal(relativeTime("it", 1000, 1000), "adesso");
assert.equal(relativeTime("en", 1000, 1000), "just now");
assert.equal(relativeTime("fr", 1000, 1000), "à l'instant");
for (const language of ["fr", "en", "it"]) {
  for (const [seconds, amount, unit] of [[120, -2, "minute"], [7200, -2, "hour"], [172800, -2, "day"]]) {
    assert.equal(
      relativeTime(language, 0, seconds * 1000),
      new Intl.RelativeTimeFormat(locale(language), { numeric: "always", style: "short" }).format(amount, unit),
    );
  }
}
console.log("Localization tests passed");

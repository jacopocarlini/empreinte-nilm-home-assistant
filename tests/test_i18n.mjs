import assert from "node:assert/strict";
import { locale, translate } from "../custom_components/empreinte/frontend/i18n.js";

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
console.log("Localization tests passed");

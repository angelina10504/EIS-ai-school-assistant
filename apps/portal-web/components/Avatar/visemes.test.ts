/**
 * Run with: npm run test:visemes
 *
 * These exist because the mapping once silently degraded to a single mouth shape
 * for every non-Latin script — the avatar looked frozen in 10 of the 11 supported
 * languages and nothing failed.
 */
import assert from "node:assert/strict";
import test from "node:test";
import { shapesForWord, visemeAt } from "./visemes.ts";

const SAMPLES: [string, string][] = [
  ["English", "attendance"],
  ["Hindi", "उपस्थिति"],
  ["Marathi", "उपस्थिती"],
  ["Tamil", "வருகை"],
  ["Telugu", "హాజరు"],
  ["Bengali", "উপস্থিতি"],
  ["Gujarati", "હાજરી"],
  ["Punjabi", "ਹਾਜ਼ਰੀ"],
  ["Kannada", "ಹಾಜರಾತಿ"],
  ["Malayalam", "ഹാജർ"],
  ["Urdu", "حاضری"],
];

test("every supported script animates, not just Latin", () => {
  for (const [language, word] of SAMPLES) {
    const shapes = shapesForWord(word);
    assert.ok(
      shapes.length >= 3,
      `${language} (${word}) produced ${shapes.length} shape(s) — the mouth would barely move`,
    );
    assert.ok(
      new Set(shapes).size >= 2,
      `${language} (${word}) never changes mouth shape`,
    );
  }
});

test("syllables are separated by a closure", () => {
  const shapes = shapesForWord("वरुका");
  for (let i = 1; i < shapes.length; i += 2) {
    assert.equal(shapes[i], "closed", "open shapes must alternate with closures");
  }
});

test("Tamil vowels map to the right mouth shapes", () => {
  // வருகை = va - ru - kai
  assert.deepEqual(
    shapesForWord("வருகை").filter((s) => s !== "closed"),
    ["wide", "round", "wide"],
  );
});

test("a virama suppresses the inherent vowel", () => {
  // नमस्ते = na - mas - te, so the conjunct releases no vowel of its own.
  assert.deepEqual(
    shapesForWord("नमस्ते").filter((s) => s !== "closed"),
    ["wide", "wide", "narrow"],
  );
});

test("shape count stays readable on a long word", () => {
  assert.ok(shapesForWord("अआइईउऊएऐओऔअआइई").length <= 15);
});

test("visemeAt walks the word and never runs off the end", () => {
  const word = "attendance";
  assert.equal(visemeAt(word, 0), shapesForWord(word)[0]);
  for (const p of [0, 0.25, 0.5, 0.99, 1, 1.5]) {
    assert.ok(shapesForWord(word).includes(visemeAt(word, p)));
  }
});

test("punctuation-only tokens still return a shape", () => {
  assert.ok(shapesForWord("—").length >= 1);
  assert.ok(shapesForWord("").length >= 1);
});

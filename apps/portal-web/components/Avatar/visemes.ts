/**
 * A deliberately small viseme set. Google Cloud TTS gives us word-level SSML mark
 * timings, not phonemes, so anything finer than this would be fake precision.
 */
export type Viseme = "closed" | "wide" | "narrow" | "round" | "rest";

export const VISEMES: Viseme[] = ["closed", "wide", "narrow", "round", "rest"];

const VOWEL_SHAPE: Record<string, Viseme> = {
  a: "wide",
  á: "wide",
  e: "narrow",
  i: "narrow",
  o: "round",
  u: "round",
  y: "narrow",
  // Devanagari / other Indic vowel signs that commonly carry the mouth shape.
  "ा": "wide",
  "ि": "narrow",
  "ी": "narrow",
  "ो": "round",
  "ू": "round",
  "ु": "round",
  "े": "narrow",
};

/** The ordered mouth shapes a single word moves through. */
export function shapesForWord(word: string): Viseme[] {
  const shapes: Viseme[] = [];
  for (const char of word.toLowerCase()) {
    const shape = VOWEL_SHAPE[char];
    if (shape && shapes[shapes.length - 1] !== shape) shapes.push(shape);
  }
  if (shapes.length === 0) shapes.push("narrow");
  // Consonant closure between syllables is what stops it looking like a puppet.
  return shapes.flatMap((shape, index) => (index === 0 ? [shape] : ["closed" as Viseme, shape]));
}

/** Which shape this word is on, given how far through it we are (0..1). */
export function visemeAt(word: string, progress: number): Viseme {
  const shapes = shapesForWord(word);
  const index = Math.min(shapes.length - 1, Math.floor(progress * shapes.length));
  return shapes[index];
}

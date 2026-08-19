/**
 * A deliberately small viseme set. Google Cloud TTS gives us word-level SSML mark
 * timings, not phonemes, so anything finer than this would be fake precision.
 */
export type Viseme = "closed" | "wide" | "narrow" | "round" | "rest";

export const VISEMES: Viseme[] = ["closed", "wide", "narrow", "round", "rest"];

/** Latin vowels. */
const LATIN_VOWEL: Record<string, Viseme> = {
  a: "wide", á: "wide", à: "wide", â: "wide",
  e: "narrow", é: "narrow", è: "narrow",
  i: "narrow", í: "narrow",
  o: "round", ó: "round", ô: "round",
  u: "round", ú: "round",
  y: "narrow",
};

/**
 * The Indic scripts we support all inherit the ISCII code layout, so a vowel sits
 * at the same offset from its block start in every one of them. That lets one
 * table cover Devanagari, Bengali, Gurmukhi, Gujarati, Tamil, Telugu, Kannada and
 * Malayalam instead of eight hand-written maps.
 */
const INDIC_BLOCKS = [
  0x0900, // Devanagari — Hindi, Marathi
  0x0980, // Bengali
  0x0a00, // Gurmukhi — Punjabi
  0x0a80, // Gujarati
  0x0b00, // Oriya
  0x0b80, // Tamil
  0x0c00, // Telugu
  0x0c80, // Kannada
  0x0d00, // Malayalam
];

/** Independent vowel letters, by offset within the block. */
const INDIC_VOWEL: Record<number, Viseme> = {
  0x05: "wide",   // a
  0x06: "wide",   // aa
  0x07: "narrow", // i
  0x08: "narrow", // ii
  0x09: "round",  // u
  0x0a: "round",  // uu
  0x0b: "narrow", // vocalic r
  0x0e: "narrow", // e (short)
  0x0f: "narrow", // e
  0x10: "wide",   // ai
  0x12: "round",  // o (short)
  0x13: "round",  // o
  0x14: "round",  // au
};

/** Dependent vowel signs (matras), by offset within the block. */
const INDIC_MATRA: Record<number, Viseme> = {
  0x3e: "wide",   // aa
  0x3f: "narrow", // i
  0x40: "narrow", // ii
  0x41: "round",  // u
  0x42: "round",  // uu
  0x43: "narrow", // vocalic r
  0x46: "narrow", // e (short)
  0x47: "narrow", // e
  0x48: "wide",   // ai
  0x4a: "round",  // o (short)
  0x4b: "round",  // o
  0x4c: "round",  // au
};

const VIRAMA_OFFSET = 0x4d;      // kills the consonant's inherent vowel
const CONSONANT_START = 0x15;
const CONSONANT_END = 0x39;

/** Urdu / Arabic script: the long vowels carry the visible mouth shape. */
const ARABIC_VOWEL: Record<string, Viseme> = {
  "ا": "wide", "آ": "wide", "أ": "wide", "ٱ": "wide",
  "و": "round", "ؤ": "round",
  "ی": "narrow", "ي": "narrow", "ے": "narrow", "ئ": "narrow",
  "ه": "wide", "ھ": "wide",
  "َ": "wide", "ِ": "narrow", "ُ": "round",
};

function indicOffset(code: number): number | null {
  for (const base of INDIC_BLOCKS) {
    if (code >= base && code < base + 0x80) return code - base;
  }
  return null;
}

/**
 * Indic syllables are consonant-plus-vowel: a bare consonant carries an inherent
 * "a" unless a matra replaces it or a virama removes it. Walking the string that
 * way gives one mouth movement per syllable, which is what makes the avatar look
 * like it is speaking Tamil rather than holding a single pose.
 */
function indicShapes(word: string): Viseme[] | null {
  const shapes: Viseme[] = [];
  let sawIndic = false;

  for (const char of word) {
    const offset = indicOffset(char.codePointAt(0)!);
    if (offset === null) continue;
    sawIndic = true;

    if (offset >= CONSONANT_START && offset <= CONSONANT_END) {
      shapes.push("wide"); // inherent 'a'
    } else if (INDIC_MATRA[offset] !== undefined) {
      if (shapes.length) shapes[shapes.length - 1] = INDIC_MATRA[offset];
      else shapes.push(INDIC_MATRA[offset]);
    } else if (INDIC_VOWEL[offset] !== undefined) {
      shapes.push(INDIC_VOWEL[offset]);
    } else if (offset === VIRAMA_OFFSET) {
      shapes.pop(); // conjunct — no vowel released here
    }
  }
  return sawIndic ? shapes : null;
}

function arabicShapes(word: string): Viseme[] | null {
  const shapes: Viseme[] = [];
  let sawArabic = false;
  for (const char of word) {
    const code = char.codePointAt(0)!;
    if (code >= 0x0600 && code <= 0x06ff) {
      sawArabic = true;
      const shape = ARABIC_VOWEL[char];
      if (shape && shapes[shapes.length - 1] !== shape) shapes.push(shape);
    }
  }
  return sawArabic ? shapes : null;
}

function latinShapes(word: string): Viseme[] {
  const shapes: Viseme[] = [];
  for (const char of word.toLowerCase()) {
    const shape = LATIN_VOWEL[char];
    if (shape && shapes[shapes.length - 1] !== shape) shapes.push(shape);
  }
  return shapes;
}

// Beyond this, shapes flick past too fast to read as speech.
const MAX_SHAPES = 8;

/** The ordered mouth shapes a single word moves through. */
export function shapesForWord(word: string): Viseme[] {
  let shapes = indicShapes(word) ?? arabicShapes(word) ?? latinShapes(word);

  if (shapes.length === 0) shapes = ["narrow"];
  if (shapes.length > MAX_SHAPES) shapes = shapes.slice(0, MAX_SHAPES);

  // Consonant closure between syllables is what stops it looking like a puppet.
  return shapes.flatMap((shape, index) => (index === 0 ? [shape] : ["closed" as Viseme, shape]));
}

/** Which shape this word is on, given how far through it we are (0..1). */
export function visemeAt(word: string, progress: number): Viseme {
  const shapes = shapesForWord(word);
  const index = Math.min(shapes.length - 1, Math.floor(progress * shapes.length));
  return shapes[index];
}

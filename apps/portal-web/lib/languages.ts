export interface LanguageOption {
  code: string;
  english: string;
  native: string;
}

export const LANGUAGES: LanguageOption[] = [
  { code: "en", english: "English", native: "English" },
  { code: "hi", english: "Hindi", native: "हिन्दी" },
  { code: "ta", english: "Tamil", native: "தமிழ்" },
  { code: "te", english: "Telugu", native: "తెలుగు" },
  { code: "mr", english: "Marathi", native: "मराठी" },
  { code: "bn", english: "Bengali", native: "বাংলা" },
  { code: "gu", english: "Gujarati", native: "ગુજરાતી" },
  { code: "pa", english: "Punjabi", native: "ਪੰਜਾਬੀ" },
  { code: "kn", english: "Kannada", native: "ಕನ್ನಡ" },
  { code: "ml", english: "Malayalam", native: "മലയാളം" },
  { code: "ur", english: "Urdu", native: "اردو" },
];

export const languageName = (code: string) =>
  LANGUAGES.find((l) => l.code === code)?.native ?? "English";

"use client";

import { LANGUAGES } from "@/lib/languages";

interface Props {
  value: string;
  onChange: (code: string) => void;
  disabled?: boolean;
}

export function LanguageSwitcher({ value, onChange, disabled }: Props) {
  return (
    <label className="lang">
      <span className="lang__caption">Language</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        aria-label="Conversation language"
      >
        {LANGUAGES.map((language) => (
          <option key={language.code} value={language.code}>
            {language.native} · {language.english}
          </option>
        ))}
      </select>
    </label>
  );
}

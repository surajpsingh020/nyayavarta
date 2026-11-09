'use client';

import React from 'react';
import { Languages } from 'lucide-react';

export interface LanguageOption {
  code: string;
  name: string;
  nativeName: string;
}

export const INDIAN_LANGUAGES: LanguageOption[] = [
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी' },
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'bn', name: 'Bengali', nativeName: 'বাংলা' },
  { code: 'ta', name: 'Tamil', nativeName: 'தமிழ்' },
  { code: 'te', name: 'Telugu', nativeName: 'తెలుగు' },
  { code: 'mr', name: 'Marathi', nativeName: 'मराठी' },
  { code: 'gu', name: 'Gujarati', nativeName: 'ગુજરાતી' },
  { code: 'kn', name: 'Kannada', nativeName: 'ಕನ್ನಡ' },
  { code: 'ml', name: 'Malayalam', nativeName: 'മലയാളം' },
  { code: 'pa', name: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ' },
  { code: 'or', name: 'Odia', nativeName: 'ଓଡ଼ିଆ' },
  { code: 'ur', name: 'Urdu', nativeName: 'اردو' },
  { code: 'as', name: 'Assamese', nativeName: 'অসমীয়া' },
  { code: 'sa', name: 'Sanskrit', nativeName: 'संस्कृतम्' },
];

interface LanguageSelectorProps {
  selectedLanguage: string;
  onLanguageChange: (code: string) => void;
  className?: string;
}

export default function LanguageSelector({
  selectedLanguage,
  onLanguageChange,
  className = '',
}: LanguageSelectorProps) {
  return (
    <div className={`relative inline-flex items-center ${className}`}>
      <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-xl px-3 py-2 shadow-sm hover:border-primary-400 transition-colors">
        <Languages className="w-5 h-5 text-primary-600 flex-shrink-0" />
        <select
          value={selectedLanguage}
          onChange={(e) => onLanguageChange(e.target.value)}
          className="bg-transparent text-sm font-medium text-gray-800 outline-none cursor-pointer pr-2"
          aria-label="Select preferred language"
        >
          {INDIAN_LANGUAGES.map((lang) => (
            <option key={lang.code} value={lang.code} className="text-gray-900">
              {lang.nativeName} ({lang.name})
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Play, Pause, Square, Volume2, VolumeX, RotateCcw } from 'lucide-react';

interface AudioPlayerProps {
  audioBase64?: string | null;
  textToSpeak?: string;
  language?: string;
  className?: string;
  autoPlay?: boolean;
}

const BCP47_LANG_MAP: Record<string, string> = {
  hi: 'hi-IN',
  en: 'en-IN',
  mr: 'mr-IN',
  bn: 'bn-IN',
  ta: 'ta-IN',
  te: 'te-IN',
  gu: 'gu-IN',
  kn: 'kn-IN',
  ml: 'ml-IN',
  pa: 'pa-IN',
  or: 'or-IN',
  ur: 'ur-IN',
  as: 'as-IN',
  sa: 'sa-IN',
};

function cleanMarkdownForSpeech(text: string): string {
  if (!text) return '';
  return text
    .replace(/#{1,6}\s+/g, '') // Remove Markdown headers
    .replace(/\*\*(.*?)\*\*/g, '$1') // Remove bold
    .replace(/\*(.*?)\*/g, '$1') // Remove italic
    .replace(/\[(.*?)\]\(.*?\)/g, '$1') // Remove links
    .replace(/^[\s*-]+/gm, '') // Remove bullet dashes
    .replace(/`/g, '') // Remove code ticks
    .replace(/\n+/g, '. ') // Turn newlines into pauses
    .trim();
}

export default function AudioPlayer({
  audioBase64,
  textToSpeak,
  language = 'hi',
  className = '',
  autoPlay = false,
}: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [useSpeechSynth, setUseSpeechSynth] = useState(true);

  // Check if speech synthesis is available in the browser
  useEffect(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      setUseSpeechSynth(true);
    } else {
      setUseSpeechSynth(false);
    }
  }, []);

  // Stop synthesis on unmount
  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const handleSpeechToggle = () => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      // Fallback to HTML Audio if speech synth is not available
      if (audioRef.current) {
        if (isPlaying) {
          audioRef.current.pause();
          setIsPlaying(false);
        } else {
          audioRef.current.play().then(() => setIsPlaying(true));
        }
      }
      return;
    }

    if (isPlaying && !isPaused) {
      window.speechSynthesis.pause();
      setIsPaused(true);
      return;
    }

    if (isPaused) {
      window.speechSynthesis.resume();
      setIsPaused(false);
      return;
    }

    // Start speaking afresh
    window.speechSynthesis.cancel();
    const cleanText = cleanMarkdownForSpeech(textToSpeak || '');
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    const bcp47 = BCP47_LANG_MAP[language.toLowerCase()] || 'hi-IN';
    utterance.lang = bcp47;
    utterance.rate = 0.95; // Slightly slower for clear legal comprehension

    // Pick best matching voice if available
    const voices = window.speechSynthesis.getVoices();
    const matchedVoice = voices.find((v) => v.lang.startsWith(language) || v.lang === bcp47);
    if (matchedVoice) {
      utterance.voice = matchedVoice;
    }

    utterance.onstart = () => {
      setIsPlaying(true);
      setIsPaused(false);
    };

    utterance.onend = () => {
      setIsPlaying(false);
      setIsPaused(false);
    };

    utterance.onerror = () => {
      setIsPlaying(false);
      setIsPaused(false);
    };

    window.speechSynthesis.speak(utterance);
  };

  const handleStop = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsPlaying(false);
    setIsPaused(false);
  };

  const audioSrc = audioBase64
    ? audioBase64.startsWith('data:')
      ? audioBase64
      : `data:audio/wav;base64,${audioBase64}`
    : undefined;

  return (
    <div
      className={`flex items-center gap-3 bg-primary-50/90 border border-primary-200 rounded-xl px-3.5 py-2 shadow-2xs ${className}`}
    >
      {audioSrc && <audio ref={audioRef} src={audioSrc} preload="none" />}

      {/* Play/Pause Button */}
      <button
        type="button"
        onClick={handleSpeechToggle}
        className="w-8 h-8 flex items-center justify-center rounded-full bg-primary-600 text-white hover:bg-primary-700 active:scale-95 transition-transform shadow-xs flex-shrink-0"
        title={isPlaying && !isPaused ? 'Pause Speech' : 'Listen to Answer'}
        aria-label={isPlaying && !isPaused ? 'Pause voice' : 'Play voice'}
      >
        {isPlaying && !isPaused ? (
          <Pause className="w-3.5 h-3.5 fill-current" />
        ) : (
          <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
        )}
      </button>

      {/* Stop Button */}
      {isPlaying && (
        <button
          type="button"
          onClick={handleStop}
          className="text-gray-500 hover:text-red-600 p-1 rounded-lg transition-colors flex-shrink-0"
          title="Stop reading"
          aria-label="Stop readout"
        >
          <Square className="w-3.5 h-3.5 fill-current" />
        </button>
      )}

      {/* Audio Status Label */}
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-primary-900 truncate">
          {isPlaying
            ? isPaused
              ? 'ध्वनि रुकी हुई है (Paused)'
              : 'कानूनी उत्तर पढ़ा जा रहा है (Speaking Guidance...)'
            : 'ध्वनि में सुनें (Listen in Voice)'}
        </p>
        <p className="text-[10px] text-primary-700 truncate">
          {isPlaying
            ? 'Browser Neural Speech Synthesizer Active'
            : 'Click play to hear full legal advice read aloud'}
        </p>
      </div>

      <Volume2 className="w-4 h-4 text-primary-600 flex-shrink-0" />
    </div>
  );
}

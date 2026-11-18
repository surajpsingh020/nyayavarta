'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Play, Pause, Square, Volume2, RotateCcw } from 'lucide-react';

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
    .replace(/\n+/g, '. ') // Turn newlines into natural pauses
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
  const activeUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Check if real audio data URI or base64 is present (> 500 characters)
  const hasRealAudio = Boolean(audioBase64 && audioBase64.length > 500);

  const audioSrc = hasRealAudio && audioBase64
    ? audioBase64.startsWith('data:')
      ? audioBase64
      : `data:audio/mp3;base64,${audioBase64}`
    : undefined;

  // Cleanup on unmount or language change
  useEffect(() => {
    return () => {
      handleStop();
    };
  }, [language, audioBase64]);

  const handleSpeechToggle = () => {
    // 1. Priority: Play high-fidelity audio from backend via HTML5 Audio element
    if (hasRealAudio && audioSrc) {
      if (isPlaying && !isPaused) {
        if (audioRef.current) audioRef.current.pause();
        setIsPaused(true);
        return;
      }

      if (isPaused && audioRef.current) {
        audioRef.current.play().then(() => {
          setIsPaused(false);
          setIsPlaying(true);
        }).catch(() => {
          playWithSpeechSynthesis();
        });
        return;
      }

      // Start fresh playback
      try {
        if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
          window.speechSynthesis.cancel();
        }

        if (!audioRef.current) {
          audioRef.current = new Audio(audioSrc);
        } else {
          audioRef.current.src = audioSrc;
        }

        audioRef.current.currentTime = 0;
        audioRef.current.onended = () => {
          setIsPlaying(false);
          setIsPaused(false);
        };
        audioRef.current.onerror = (e) => {
          console.warn('HTML5 audio error, falling back to Web Speech API:', e);
          playWithSpeechSynthesis();
        };

        audioRef.current.play().then(() => {
          setIsPlaying(true);
          setIsPaused(false);
        }).catch((err) => {
          console.warn('HTML5 audio play blocked/failed, falling back to Web Speech API:', err);
          playWithSpeechSynthesis();
        });
        return;
      } catch (err) {
        console.warn('Audio tag setup error:', err);
        playWithSpeechSynthesis();
        return;
      }
    }

    // 2. Fallback: Web Speech API
    playWithSpeechSynthesis();
  };

  const playWithSpeechSynthesis = () => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      alert('Speech audio is not supported in this browser.');
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

    window.speechSynthesis.cancel();
    if (audioRef.current) {
      audioRef.current.pause();
    }

    const cleanText = cleanMarkdownForSpeech(textToSpeak || '');
    if (!cleanText) return;

    // Chunk text by sentences to prevent Chromium 15-second freeze bug
    const sentences = cleanText.match(/[^.!?।]+[.!?।]+|[^.!?।]+/g) || [cleanText];
    const bcp47 = BCP47_LANG_MAP[language.toLowerCase()] || 'hi-IN';
    const voices = window.speechSynthesis.getVoices();
    const matchedVoice = voices.find((v) =>
      v.lang.toLowerCase() === bcp47.toLowerCase() ||
      v.lang.toLowerCase().startsWith(language.toLowerCase())
    );

    let currentIndex = 0;

    const speakNextChunk = () => {
      if (currentIndex >= sentences.length) {
        setIsPlaying(false);
        setIsPaused(false);
        activeUtteranceRef.current = null;
        return;
      }

      const chunk = sentences[currentIndex].trim();
      if (!chunk) {
        currentIndex++;
        speakNextChunk();
        return;
      }

      const utterance = new SpeechSynthesisUtterance(chunk);
      activeUtteranceRef.current = utterance; // Prevent Chrome garbage collection bug
      utterance.lang = bcp47;
      utterance.rate = 0.95;
      if (matchedVoice) {
        utterance.voice = matchedVoice;
      }

      utterance.onend = () => {
        currentIndex++;
        speakNextChunk();
      };

      utterance.onerror = () => {
        setIsPlaying(false);
        setIsPaused(false);
        activeUtteranceRef.current = null;
      };

      window.speechSynthesis.speak(utterance);
    };

    setIsPlaying(true);
    setIsPaused(false);
    speakNextChunk();
  };

  const handleStop = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    activeUtteranceRef.current = null;
    setIsPlaying(false);
    setIsPaused(false);
  };

  return (
    <div
      className={`flex items-center gap-3 bg-primary-50/90 border border-primary-200 rounded-xl px-3.5 py-2 shadow-2xs ${className}`}
    >
      {/* Hidden audio element for HTML5 Audio playback */}
      {audioSrc && (
        <audio
          ref={audioRef}
          src={audioSrc}
          preload="auto"
          onEnded={() => {
            setIsPlaying(false);
            setIsPaused(false);
          }}
        />
      )}

      {/* Play/Pause Button */}
      <button
        type="button"
        onClick={handleSpeechToggle}
        className="w-8 h-8 flex items-center justify-center rounded-full bg-primary-600 text-white hover:bg-primary-700 active:scale-95 transition-transform shadow-xs flex-shrink-0"
        title={isPlaying && !isPaused ? 'Pause Voice' : 'Listen to Answer in Voice'}
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
              ? language === 'en'
                ? 'Voice Paused'
                : 'ध्वनि रुकी हुई है (Paused)'
              : language === 'en'
                ? 'Reading Legal Guidance Aloud...'
                : 'कानूनी उत्तर पढ़ा जा रहा है (Speaking Guidance...)'
            : language === 'en'
              ? 'Listen in Voice (Read Aloud)'
              : 'ध्वनि में सुनें (Listen in Voice)'}
        </p>
        <p className="text-[10px] text-primary-700 truncate">
          {isPlaying
            ? hasRealAudio
              ? 'High-Fidelity Indian Voice Active'
              : 'Browser Speech Synthesizer Active'
            : language === 'en'
              ? 'Click play to hear full legal advice read aloud'
              : 'पूरा कानूनी उत्तर सुनने के लिए प्ले बटन दबाएं'}
        </p>
      </div>

      <Volume2 className="w-4 h-4 text-primary-600 flex-shrink-0" />
    </div>
  );
}

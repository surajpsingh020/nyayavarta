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
  const lines = text.split('\n');
  const cleanedLines: string[] = [];
  let inTable = false;
  let tableHeaders: string[] = [];

  for (const line of lines) {
    const stripped = line.trim();
    if (!stripped) continue;
    // Skip markdown table border/separator lines
    if (/^\|?\s*[-:]+\s*(\|[-:\s]+)+\|?$/.test(stripped)) continue;
    // Process table row
    if (stripped.startsWith('|') && stripped.endsWith('|')) {
      const cells = stripped.split('|').slice(1, -1).map((c) => c.trim());
      if (!inTable) {
        tableHeaders = cells;
        inTable = true;
      } else {
        const rowParts: string[] = [];
        cells.forEach((val) => {
          if (val && val !== '-' && val !== '—') {
            rowParts.push(val);
          }
        });
        if (rowParts.length > 0) {
          cleanedLines.push(rowParts.join(', ') + '.');
        }
      }
    } else {
      inTable = false;
      let lineClean = stripped.replace(/^#+\s*/, '');
      lineClean = lineClean.replace(/\*\*([^*]+)\*\*/g, '$1');
      lineClean = lineClean.replace(/\*([^*]+)\*/g, '$1');
      lineClean = lineClean.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
      lineClean = lineClean.replace(/^[-*•\d\.]+\s*/, '');
      lineClean = lineClean.replace(/[`_]/g, '');
      lineClean = lineClean.replace(/https?:\/\/\S+/g, '');
      if (lineClean.trim()) {
        cleanedLines.push(lineClean.trim());
      }
    }
  }

  return cleanedLines.join('. ').replace(/\s+/g, ' ').trim();
}

const AUDIO_LABELS: Record<string, { listen: string; playPrompt: string; paused: string; reading: string }> = {
  en: {
    listen: 'Listen in Voice (Read Aloud)',
    playPrompt: 'Click play to hear full legal advice read aloud',
    paused: 'Voice Paused',
    reading: 'Reading Legal Guidance Aloud...',
  },
  hi: {
    listen: 'ध्वनि में सुनें (Listen in Voice)',
    playPrompt: 'पूरा कानूनी उत्तर सुनने के लिए प्ले बटन दबाएं',
    paused: 'ध्वनि रुकी हुई है (Paused)',
    reading: 'कानूनी उत्तर पढ़ा जा रहा है (Speaking Guidance...)',
  },
  bn: {
    listen: 'কণ্ঠে শুনুন (Listen in Voice)',
    playPrompt: 'সম্পূর্ণ আইনি পরামর্শ শুনতে প্লে বোতামে চাপুন',
    paused: 'কণ্ঠ স্থগিত (Paused)',
    reading: 'আইনি পরামর্শ পাঠ করা হচ্ছে (Speaking Guidance...)',
  },
  te: {
    listen: 'వాయిస్‌లో వినండి (Listen in Voice)',
    playPrompt: 'పూర్తి చట్టపరమైన సలహా వినడానికి ప్లే నొక్కండి',
    paused: 'వాయిస్ నిలిపివేయబడింది (Paused)',
    reading: 'చట్టపరమైన సలహా చదవబడుతోంది (Speaking...)',
  },
  ta: {
    listen: 'குரலில் கேளுங்கள் (Listen in Voice)',
    playPrompt: 'முழு சட்ட ஆலோசனையையும் கேட்க பிளே பொத்தானை அழுத்தவும்',
    paused: 'குரல் இடைநிறுத்தப்பட்டது (Paused)',
    reading: 'சட்ட ஆலோசனை வாசிக்கப்படுகிறது (Speaking...)',
  },
  mr: {
    listen: 'आवाजात ऐका (Listen in Voice)',
    playPrompt: 'पूर्ण कायदेशीर सल्ला ऐकण्यासाठी प्ले बटण दाबा',
    paused: 'आवाज थांबवला आहे (Paused)',
    reading: 'कायदेशीर सल्ला वाचला जात आहे (Speaking...)',
  },
  gu: {
    listen: 'અવાજમાં સાંભળો (Listen in Voice)',
    playPrompt: 'સંપૂર્ણ કાનૂની સલાહ સાંભળવા માટે પ્લે બટન દબાવો',
    paused: 'અવાજ થોભાવેલ છે (Paused)',
    reading: 'કાનૂની સલાહ વાંચવામાં આવી રહી છે (Speaking...)',
  },
  kn: {
    listen: 'ಧ್ವನಿಯಲ್ಲಿ ಕೇಳಿ (Listen in Voice)',
    playPrompt: 'ಸಂಪೂರ್ಣ ಕಾನೂನು ಸಲಹೆಯನ್ನು ಕೇಳಲು ಪ್ಲೇ ಬಟನ್ ಒತ್ತಿರಿ',
    paused: 'ಧ್ವನಿ ವಿರಾಮಗೊಳಿಸಲಾಗಿದೆ (Paused)',
    reading: 'ಕಾನೂನು ಸಲಹೆ ಓದಲಾಗುತ್ತಿದೆ (Speaking...)',
  },
  ml: {
    listen: 'ശബ്ദത്തിൽ കേൾക്കുക (Listen in Voice)',
    playPrompt: 'പൂർണ്ണ നിയമോപദേശം കേൾക്കാൻ പ്ലേ അമർത്തുക',
    paused: 'ശബ്ദം താൽക്കാലികമായി നിർത്തി (Paused)',
    reading: 'നിയമോപദേശം വായിക്കുന്നു (Speaking...)',
  },
  pa: {
    listen: 'ਆਵਾਜ਼ ਵਿੱਚ ਸੁਣੋ (Listen in Voice)',
    playPrompt: 'ਪੂਰੀ ਕਾਨੂੰਨੀ ਸਲਾਹ ਸੁਣਨ ਲਈ ਪਲੇ ਬਟਨ ਦਬਾਓ',
    paused: 'ਆਵਾਜ਼ ਰੋਕੀ ਗਈ (Paused)',
    reading: 'ਕਾਨੂੰਨੀ ਸਲਾਹ ਪੜ੍ਹੀ ਜਾ ਰਹੀ ਹੈ (Speaking...)',
  },
  or: {
    listen: 'ଶବ୍ଦରେ ଶୁଣନ୍ତୁ (Listen in Voice)',
    playPrompt: 'ସମ୍ପୂର୍ଣ୍ଣ ଆଇନଗତ ପରାମର୍ଶ ଶୁଣିବା ପାଇଁ ପ୍ଲେ ବଟନ୍ ଦବାନ୍ତୁ',
    paused: 'ଶବ୍ଦ ବନ୍ଦ ହୋଇଛି (Paused)',
    reading: 'ଆଇନଗତ ପରାମର୍ଶ ପଢାଯାଉଛି (Speaking...)',
  },
  ur: {
    listen: 'آواز میں سنیں (Listen in Voice)',
    playPrompt: 'مکمل قانونی مشورہ سننے کے لیے پلے کا بٹن دبائیں',
    paused: 'آواز روکی گئی (Paused)',
    reading: 'قانونی مشورہ پڑھا جا رہا ہے (Speaking...)',
  },
  as: {
    listen: 'শব্দত শুনক (Listen in Voice)',
    playPrompt: 'সম্পূৰ্ণ আইনী পৰামৰ্শ শুনিবলৈ প্লে বুটাম টিপক',
    paused: 'শব্দ স্থগিত (Paused)',
    reading: 'আইনী পৰামৰ্শ পাঠ কৰা হৈছে (Speaking...)',
  },
  sa: {
    listen: 'स्वरेण शृण्वन्तु (Listen in Voice)',
    playPrompt: 'सम्पूर्णां विधिक-परामर्शं श्रोतुं प्ले-बटनं नुदन्तु',
    paused: 'स्वरः स्थगितः (Paused)',
    reading: 'विधिक-परामर्शः पठ्यते (Speaking...)',
  },
};

export default function AudioPlayer({
  audioBase64,
  textToSpeak,
  language = 'hi',
  className = '',
  autoPlay = false,
}: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const audioInstanceRef = useRef<HTMLAudioElement | null>(null);
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

  const handleStop = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    if (audioInstanceRef.current) {
      audioInstanceRef.current.pause();
      audioInstanceRef.current.currentTime = 0;
      audioInstanceRef.current = null;
    }
    activeUtteranceRef.current = null;
    setIsPlaying(false);
    setIsPaused(false);
  };

  const handleSpeechToggle = () => {
    // 1. If currently playing, pause
    if (isPlaying && !isPaused) {
      if (audioInstanceRef.current) {
        audioInstanceRef.current.pause();
      } else if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.pause();
      }
      setIsPaused(true);
      return;
    }

    // 2. If paused, resume
    if (isPaused) {
      if (audioInstanceRef.current) {
        audioInstanceRef.current.play().then(() => {
          setIsPaused(false);
          setIsPlaying(true);
        }).catch(() => {
          playWithSpeechSynthesis();
        });
        return;
      }
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.resume();
        setIsPaused(false);
        setIsPlaying(true);
        return;
      }
    }

    // 3. Start fresh playback
    handleStop();

    // Priority: Play high-fidelity backend MP3 audio via Audio instance
    if (hasRealAudio && audioSrc) {
      try {
        const sound = new Audio(audioSrc);
        audioInstanceRef.current = sound;
        sound.onended = () => {
          setIsPlaying(false);
          setIsPaused(false);
          audioInstanceRef.current = null;
        };
        sound.onerror = (e) => {
          console.warn('HTML5 audio error, falling back to Web Speech API:', e);
          audioInstanceRef.current = null;
          playWithSpeechSynthesis();
        };

        sound.play().then(() => {
          setIsPlaying(true);
          setIsPaused(false);
        }).catch((err) => {
          console.warn('HTML5 audio play blocked/failed, falling back to Web Speech API:', err);
          audioInstanceRef.current = null;
          playWithSpeechSynthesis();
        });
        return;
      } catch (err) {
        console.warn('Audio tag setup error:', err);
        playWithSpeechSynthesis();
        return;
      }
    }

    // Fallback: Web Speech API
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
    if (audioInstanceRef.current) {
      audioInstanceRef.current.pause();
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

  return (
    <div
      className={`flex items-center gap-3 bg-primary-50/90 border border-primary-200 rounded-xl px-3.5 py-2 shadow-2xs ${className}`}
    >
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
          {(() => {
            const lbl = AUDIO_LABELS[language] || AUDIO_LABELS.en;
            if (isPlaying) {
              return isPaused ? lbl.paused : lbl.reading;
            }
            return lbl.listen;
          })()}
        </p>
        <p className="text-[10px] text-primary-700 truncate">
          {isPlaying
            ? hasRealAudio
              ? 'High-Fidelity Indian Voice Active'
              : 'Browser Speech Synthesizer Active'
            : (AUDIO_LABELS[language] || AUDIO_LABELS.en).playPrompt}
        </p>
      </div>

      <Volume2 className="w-4 h-4 text-primary-600 flex-shrink-0" />
    </div>
  );
}

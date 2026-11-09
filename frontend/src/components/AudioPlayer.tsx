'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Play, Pause, RotateCcw, Volume2, VolumeX } from 'lucide-react';

interface AudioPlayerProps {
  audioBase64: string;
  className?: string;
  autoPlay?: boolean;
}

export default function AudioPlayer({
  audioBase64,
  className = '',
  autoPlay = false,
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isMuted, setIsMuted] = useState(false);

  const audioSrc = audioBase64.startsWith('data:')
    ? audioBase64
    : `data:audio/wav;base64,${audioBase64}`;

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onLoadedMetadata = () => {
      setDuration(audio.duration || 0);
      if (autoPlay) {
        audio.play().catch(() => {
          // Browser may block unprompted autoplay
        });
      }
    };

    const onTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };

    const onEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('ended', onEnded);

    return () => {
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('ended', onEnded);
    };
  }, [audioSrc, autoPlay]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio.play().then(() => setIsPlaying(true)).catch((err) => {
        console.warn('Audio playback error:', err);
      });
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  };

  const toggleMute = () => {
    if (!audioRef.current) return;
    audioRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const handleRestart = () => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = 0;
    setCurrentTime(0);
    audioRef.current.play().then(() => setIsPlaying(true));
  };

  const formatTime = (secs: number) => {
    if (isNaN(secs) || secs === 0) return '0:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div
      className={`flex items-center gap-3 bg-primary-50/80 border border-primary-200/80 rounded-2xl px-4 py-2.5 shadow-sm ${className}`}
    >
      <audio ref={audioRef} src={audioSrc} preload="metadata" />

      {/* Play/Pause Button */}
      <button
        type="button"
        onClick={togglePlay}
        className="w-9 h-9 flex items-center justify-center rounded-full bg-primary-600 text-white hover:bg-primary-700 active:scale-95 transition-transform shadow flex-shrink-0"
        aria-label={isPlaying ? 'Pause audio' : 'Play audio'}
      >
        {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
      </button>

      {/* Restart */}
      <button
        type="button"
        onClick={handleRestart}
        className="text-gray-500 hover:text-gray-700 p-1 rounded-lg transition-colors flex-shrink-0"
        title="Replay from start"
      >
        <RotateCcw className="w-3.5 h-3.5" />
      </button>

      {/* Time & Scrubber */}
      <div className="flex-1 flex items-center gap-2 min-w-0">
        <input
          type="range"
          min={0}
          max={duration || 1}
          step={0.1}
          value={currentTime}
          onChange={handleSeek}
          className="w-full h-1.5 bg-primary-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
          aria-label="Audio progress scrubber"
        />
        <span className="text-[11px] font-medium text-primary-900 tabular-nums flex-shrink-0">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>

      {/* Volume toggle */}
      <button
        type="button"
        onClick={toggleMute}
        className="text-gray-500 hover:text-gray-700 p-1 rounded-lg transition-colors flex-shrink-0"
        aria-label={isMuted ? 'Unmute' : 'Mute'}
      >
        {isMuted ? <VolumeX className="w-4 h-4 text-red-500" /> : <Volume2 className="w-4 h-4" />}
      </button>
    </div>
  );
}

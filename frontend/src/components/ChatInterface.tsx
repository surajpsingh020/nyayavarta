'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Mic,
  Square,
  Volume2,
  Languages,
  Copy,
  Check,
  Scale,
  Sparkles,
  PhoneCall,
  Loader2,
  Trash2,
  HelpCircle,
} from 'lucide-react';
import {
  sendChatMessage,
  MessageItem,
  UserProfileType,
  ChatResponse,
} from '@/lib/api';
import { getUITranslations } from '@/lib/i18n';
import AudioPlayer from './AudioPlayer';
import CitationCard from './CitationCard';

interface ChatInterfaceProps {
  selectedLanguage: string;
  selectedProfile: UserProfileType;
  className?: string;
}

export default function ChatInterface({
  selectedLanguage,
  selectedProfile,
  className = '',
}: ChatInterfaceProps) {
  const t = getUITranslations(selectedLanguage);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Per-message language toggle: { [messageId]: 'regional' | 'english' }
  const [languageToggleMap, setLanguageToggleMap] = useState<Record<string, 'regional' | 'english'>>({});

  // Voice recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordDuration, setRecordDuration] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordTimerRef = useRef<NodeJS.Timeout | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (recordTimerRef.current) clearInterval(recordTimerRef.current);
    };
  }, []);

  const handleCopyText = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const toggleLanguageView = (messageId: string) => {
    setLanguageToggleMap((prev) => ({
      ...prev,
      [messageId]: prev[messageId] === 'english' ? 'regional' : 'english',
    }));
  };

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim();
    if (!text || isLoading) return;

    const userMessageId = 'msg-' + Date.now();
    const newUserMessage: MessageItem = {
      id: userMessageId,
      sender: 'user',
      originalQuery: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const response: ChatResponse = await sendChatMessage({
        text,
        source_language: selectedLanguage,
        user_profile: selectedProfile,
      });

      const assistantMessageId = 'resp-' + Date.now();
      const newAssistantMessage: MessageItem = {
        id: assistantMessageId,
        sender: 'assistant',
        originalQuery: response.original_query,
        englishQuery: response.english_query,
        regionalResponse: response.regional_response,
        englishResponse: response.english_response,
        citations: response.citations,
        audioBase64: response.audio_base64,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, newAssistantMessage]);
      setLanguageToggleMap((prev) => ({
        ...prev,
        [assistantMessageId]: 'regional',
      }));
    } catch (err: any) {
      const errorMessageId = 'err-' + Date.now();
      setMessages((prev) => [
        ...prev,
        {
          id: errorMessageId,
          sender: 'assistant',
          regionalResponse: `त्रुटि (Error): ${err.message || 'Unable to connect to legal AI service.'}`,
          englishResponse: `Error: ${err.message || 'Unable to connect to legal AI service.'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // -------------------------------------------------------------
  // Voice Recording via MediaRecorder API
  // -------------------------------------------------------------
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });

        // Convert Blob to Base64
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = async () => {
          const base64Data = (reader.result as string).split(',')[1];
          if (base64Data) {
            await handleSendAudioMessage(base64Data);
          }
        };
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordDuration(0);

      recordTimerRef.current = setInterval(() => {
        setRecordDuration((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      alert('Microphone access is required for voice query. Please enable mic permissions in your browser.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (recordTimerRef.current) {
        clearInterval(recordTimerRef.current);
      }
    }
  };

  const handleSendAudioMessage = async (audioBase64: string) => {
    const userMessageId = 'msg-audio-' + Date.now();
    const newUserMessage: MessageItem = {
      id: userMessageId,
      sender: 'user',
      originalQuery: '🎤 [Voice Query / ध्वनि प्रश्न]',
      isAudioQuery: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setIsLoading(true);

    try {
      const response: ChatResponse = await sendChatMessage({
        audio_base64: audioBase64,
        source_language: selectedLanguage,
        user_profile: selectedProfile,
      });

      const assistantMessageId = 'resp-' + Date.now();
      const newAssistantMessage: MessageItem = {
        id: assistantMessageId,
        sender: 'assistant',
        originalQuery: response.original_query,
        englishQuery: response.english_query,
        regionalResponse: response.regional_response,
        englishResponse: response.english_response,
        citations: response.citations,
        audioBase64: response.audio_base64,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, newAssistantMessage]);
      setLanguageToggleMap((prev) => ({
        ...prev,
        [assistantMessageId]: 'regional',
      }));
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: 'err-' + Date.now(),
          sender: 'assistant',
          regionalResponse: `त्रुटि (Error): ${err.message || 'Speech recognition processing failed.'}`,
          englishResponse: `Error: ${err.message || 'Speech recognition processing failed.'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    if (confirm('Clear the current legal consultation conversation?')) {
      setMessages([]);
    }
  };

  return (
    <div className={`flex flex-col h-[700px] bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden ${className}`}>
      {/* Chat Header */}
      <div className="px-5 py-3.5 bg-gradient-to-r from-primary-900 via-primary-800 to-primary-900 text-white flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center border border-white/20">
            <Scale className="w-5 h-5 text-accent-300" />
          </div>
          <div>
            <h2 className="text-base font-bold tracking-tight flex items-center gap-2">
              {t.chatHeader}
              <span className="text-[10px] bg-accent-500/20 text-accent-200 border border-accent-400/30 px-2 py-0.5 rounded-full font-medium">
                Live RAG
              </span>
            </h2>
            <p className="text-[11px] text-primary-200">
              {t.chatSubtitle}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              type="button"
              onClick={clearChat}
              className="p-1.5 text-primary-200 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
              title="Clear conversation"
              aria-label="Clear chat"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Messages Thread */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-5 bg-gray-50/50">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-5">
            <div className="w-14 h-14 rounded-2xl bg-primary-100 flex items-center justify-center text-primary-600 shadow-inner">
              <Sparkles className="w-7 h-7" />
            </div>
            <div className="max-w-md space-y-1.5">
              <h3 className="text-lg font-bold text-gray-800">
                {t.chatGreeting}
              </h3>
              <p className="text-xs text-gray-500 leading-relaxed">
                {t.chatGreetingSub}
              </p>
            </div>

            {/* Quick Sample Prompts */}
            <div className="w-full max-w-xl text-left space-y-2 mt-2">
              <span className="text-[11px] font-semibold uppercase text-gray-400 tracking-wider block">
                {t.suggestedQueriesTitle}
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {t.suggestedQueries.map((prompt, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSendMessage(prompt.text)}
                    className="p-2.5 rounded-xl border border-gray-200 bg-white hover:border-primary-400 hover:bg-primary-50/50 text-left transition-all text-xs text-gray-700 shadow-2xs group"
                  >
                    <span className="font-semibold text-primary-700 block mb-0.5 group-hover:text-primary-800">
                      {prompt.label}
                    </span>
                    <span className="line-clamp-2 text-gray-600 text-[11px]">
                      "{prompt.text}"
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.sender === 'user';
            const currentLang = languageToggleMap[msg.id] || 'regional';
            const displayText =
              currentLang === 'english'
                ? msg.englishResponse || msg.regionalResponse || ''
                : msg.regionalResponse || msg.englishResponse || '';

            return (
              <div
                key={msg.id}
                className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-[85%] md:max-w-[75%] rounded-2xl p-4 shadow-xs ${
                    isUser
                      ? 'bg-primary-600 text-white rounded-br-xs'
                      : 'bg-white border border-gray-200/90 text-gray-900 rounded-bl-xs'
                  }`}
                >
                  {isUser ? (
                    <div className="space-y-1">
                      <p className="text-sm font-medium whitespace-pre-wrap leading-relaxed">
                        {msg.originalQuery}
                      </p>
                      <span className="text-[10px] text-primary-200 block text-right mt-1">
                        {msg.timestamp}
                      </span>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {/* Assistant Header / Controls */}
                      <div className="flex items-center justify-between border-b border-gray-100 pb-2 gap-2">
                        <div className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-primary-600" />
                          <span className="text-xs font-bold text-primary-900">
                            Nyayavarta Legal Guidance
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5">
                          {/* Bilingual Toggle Button */}
                          {msg.englishResponse && msg.regionalResponse && (
                            <button
                              type="button"
                              onClick={() => toggleLanguageView(msg.id)}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-semibold bg-primary-50 text-primary-700 border border-primary-200 hover:bg-primary-100 transition-colors"
                              title="Switch language view"
                            >
                              <Languages className="w-3 h-3" />
                              {currentLang === 'english' ? 'View Regional' : 'View English'}
                            </button>
                          )}

                          {/* Copy button */}
                          <button
                            type="button"
                            onClick={() => handleCopyText(msg.id, displayText)}
                            className="p-1 text-gray-400 hover:text-gray-700 rounded transition-colors"
                            title="Copy legal response"
                            aria-label="Copy response"
                          >
                            {copiedId === msg.id ? (
                              <Check className="w-3.5 h-3.5 text-green-600" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </div>

                      {/* Response Body */}
                      <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap space-y-2">
                        {displayText}
                      </div>

                      {/* Inline Audio Player (TTS Voice Response) */}
                      {msg.audioBase64 && (
                        <div className="mt-2 pt-2 border-t border-gray-100">
                          <span className="text-[11px] font-semibold text-primary-800 flex items-center gap-1 mb-1.5">
                            <Volume2 className="w-3.5 h-3.5" />
                            Listen in Audio (वाणी में सुनें)
                          </span>
                          <AudioPlayer audioBase64={msg.audioBase64} />
                        </div>
                      )}

                      {/* Citations Card */}
                      {msg.citations && msg.citations.length > 0 && (
                        <CitationCard citations={msg.citations} />
                      )}

                      {/* Timestamp & Legal Aid banner */}
                      <div className="flex items-center justify-between pt-1 text-[10px] text-gray-400">
                        <span className="flex items-center gap-1 text-amber-700 font-medium">
                          <PhoneCall className="w-3 h-3" />
                          National Legal Aid: 15100 (Toll-Free)
                        </span>
                        <span>{msg.timestamp}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-start gap-2">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-xs p-4 shadow-xs flex items-center gap-3">
              <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />
              <div className="space-y-0.5">
                <p className="text-xs font-semibold text-gray-800">
                  Analyzing legal statutes & synthesizing citations...
                </p>
                <p className="text-[11px] text-gray-400">
                  Retrieving BNS/BNSS/BSA law transitions with Gemini 3.8 Flash
                </p>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-3.5 md:p-4 bg-white border-t border-gray-200 space-y-2.5">
        {/* Voice recording banner if recording */}
        {isRecording && (
          <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-xl px-4 py-2 animate-pulse">
            <div className="flex items-center gap-2 text-red-700 text-xs font-semibold">
              <span className="w-2.5 h-2.5 rounded-full bg-red-600" />
              {t.listening} ({recordDuration}s)
            </div>
            <button
              type="button"
              onClick={stopRecording}
              className="flex items-center gap-1 text-xs font-bold bg-red-600 text-white px-3 py-1 rounded-lg hover:bg-red-700"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              {t.stopSend}
            </button>
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center gap-2"
        >
          {/* Microphone button */}
          <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isLoading}
            className={`p-3 rounded-xl border-2 transition-all flex-shrink-0 flex items-center justify-center ${
              isRecording
                ? 'border-red-500 bg-red-500 text-white animate-bounce'
                : 'border-gray-200 text-gray-600 hover:border-primary-500 hover:text-primary-600 hover:bg-primary-50'
            } disabled:opacity-50`}
            title={isRecording ? t.stopSend : 'Speak your query (बोलकर पूछें)'}
            aria-label="Microphone record button"
          >
            <Mic className="w-5 h-5" />
          </button>

          {/* Text Input */}
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={t.inputPlaceholder}
            disabled={isLoading || isRecording}
            className="flex-1 px-4 py-3 bg-gray-50 border-2 border-gray-200 rounded-xl text-sm text-gray-900 focus:bg-white focus:border-primary-500 focus:ring-4 focus:ring-primary-100 outline-none transition-all placeholder:text-gray-400 disabled:opacity-50"
          />

          {/* Send Button */}
          <button
            type="submit"
            disabled={isLoading || !inputText.trim() || isRecording}
            className="p-3 bg-primary-600 hover:bg-primary-700 active:scale-95 text-white rounded-xl font-medium transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
            aria-label="Send query"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>

        <div className="flex items-center justify-between text-[11px] text-gray-400 px-1">
          <span>Supported: Voice & text in 22 scheduled Indian languages</span>
          <span>Legal Aid Toll-Free: 15100</span>
        </div>
      </div>
    </div>
  );
}

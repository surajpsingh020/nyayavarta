'use client';

import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
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
  Paperclip,
  FileText,
  X,
  CheckCircle2,
} from 'lucide-react';
import {
  sendChatMessage,
  uploadDocument,
  MessageItem,
  ChatResponse,
  UploadResponse,
} from '@/lib/api';
import { getUITranslations } from '@/lib/i18n';
import AudioPlayer from './AudioPlayer';
import CitationCard from './CitationCard';

interface ChatInterfaceProps {
  selectedLanguage: string;
  className?: string;
}

const BCP47_SPEECH_MAP: Record<string, string> = {
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

export default function ChatInterface({
  selectedLanguage,
  className = '',
}: ChatInterfaceProps) {
  const t = getUITranslations(selectedLanguage);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Per-message language toggle: { [messageId]: 'regional' | 'english' }
  const [languageToggleMap, setLanguageToggleMap] = useState<Record<string, 'regional' | 'english'>>({});

  // Document Attachment State in Chat
  const [isUploadingDoc, setIsUploadingDoc] = useState(false);
  const [attachedDoc, setAttachedDoc] = useState<UploadResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Voice recording & Web Speech Recognition state
  const [isListening, setIsListening] = useState(false);
  const [speechInterim, setSpeechInterim] = useState('');
  const speechRecognitionRef = useRef<any>(null);

  // MediaRecorder Fallback
  const [isMediaRecording, setIsMediaRecording] = useState(false);
  const [recordDuration, setRecordDuration] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordTimerRef = useRef<NodeJS.Timeout | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, isListening]);

  // Clean up timers & speech recognition on unmount
  useEffect(() => {
    return () => {
      if (recordTimerRef.current) clearInterval(recordTimerRef.current);
      if (speechRecognitionRef.current) {
        try {
          speechRecognitionRef.current.stop();
        } catch {}
      }
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

  // -------------------------------------------------------------
  // Document Upload Directly in Chat
  // -------------------------------------------------------------
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploadingDoc(true);
    try {
      const res = await uploadDocument(file);
      setAttachedDoc(res);

      // Add a system announcement message in the chat
      const sysMsgId = 'sys-' + Date.now();
      setMessages((prev) => [
        ...prev,
        {
          id: sysMsgId,
          sender: 'assistant',
          regionalResponse: `📄 **दस्तावेज़ सफलतापूर्वक इंडेक्स किया गया**: "${res.filename}"\n\n- **इंडेक्स किए गए भाग**: ${res.chunks_created} Chunks\n- **नॉलेज ग्राफ स्थिति**: Neo4j ग्राफ में संबंधित कानूनी धाराओं (Sections) से जोड़ा गया।\n\nअब आप इस दस्तावेज़ से संबंधित कोई भी कानूनी प्रश्न पूछ सकते हैं! (उदाहरण: "इस रिपोर्ट में कौन-सी धाराएं लगी हैं?", "FIR के मुख्य आरोप क्या हैं?")`,
          englishResponse: `📄 **Document Successfully Indexed**: "${res.filename}"\n\n- **Indexed Chunks**: ${res.chunks_created} Chunks\n- **Knowledge Graph Status**: Linked to statutory Sections in Neo4j.\n\nYou can now ask legal queries about this document! (e.g., "Summarize the key charges in this report", "What sections apply?")`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } catch (err: any) {
      alert(`Document upload failed: ${err.message || 'Server error'}`);
    } finally {
      setIsUploadingDoc(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const removeAttachedDoc = () => {
    setAttachedDoc(null);
  };

  // -------------------------------------------------------------
  // Send Chat Message
  // -------------------------------------------------------------
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
    setSpeechInterim('');
    setIsLoading(true);

    try {
      const response: ChatResponse = await sendChatMessage({
        text,
        source_language: selectedLanguage,
        user_profile: 'general',
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
  // Web Speech API: Real-Time Voice Recognition (Speech-to-Text)
  // -------------------------------------------------------------
  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const startListening = () => {
    const SpeechRecognition =
      (typeof window !== 'undefined' &&
        ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition)) ||
      null;

    if (!SpeechRecognition) {
      // Fallback to MediaRecorder if Web Speech is unsupported
      startMediaRecording();
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      speechRecognitionRef.current = recognition;
      recognition.continuous = false;
      recognition.interimResults = true;

      const langCode = BCP47_SPEECH_MAP[selectedLanguage.toLowerCase()] || 'hi-IN';
      recognition.lang = langCode;

      recognition.onstart = () => {
        setIsListening(true);
        setSpeechInterim('');
      };

      recognition.onresult = (event: any) => {
        let interim = '';
        let final = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            final += event.results[i][0].transcript;
          } else {
            interim += event.results[i][0].transcript;
          }
        }

        if (final) {
          setInputText((prev) => (prev ? `${prev} ${final.trim()}` : final.trim()));
          setSpeechInterim('');
        } else {
          setSpeechInterim(interim);
        }
      };

      recognition.onerror = (event: any) => {
        console.warn('Speech recognition error:', event.error);
        setIsListening(false);
        setSpeechInterim('');
      };

      recognition.onend = () => {
        setIsListening(false);
        setSpeechInterim('');
      };

      recognition.start();
    } catch (err) {
      console.warn('Speech recognition start failed, using fallback:', err);
      startMediaRecording();
    }
  };

  const stopListening = () => {
    if (speechRecognitionRef.current) {
      try {
        speechRecognitionRef.current.stop();
      } catch {}
    }
    setIsListening(false);
    setSpeechInterim('');
  };

  // -------------------------------------------------------------
  // MediaRecorder Fallback
  // -------------------------------------------------------------
  const startMediaRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });

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
      setIsMediaRecording(true);
      setRecordDuration(0);

      recordTimerRef.current = setInterval(() => {
        setRecordDuration((prev) => prev + 1);
      }, 1000);
    } catch {
      alert('Microphone access is required for voice queries. Please grant microphone permission in your browser.');
    }
  };

  const stopMediaRecording = () => {
    if (mediaRecorderRef.current && isMediaRecording) {
      mediaRecorderRef.current.stop();
      setIsMediaRecording(false);
      if (recordTimerRef.current) clearInterval(recordTimerRef.current);
    }
  };

  const handleSendAudioMessage = async (audioBase64: string) => {
    const userMessageId = 'msg-audio-' + Date.now();
    const newUserMessage: MessageItem = {
      id: userMessageId,
      sender: 'user',
      originalQuery: '🎤 [ध्वनि प्रश्न / Voice Query]',
      isAudioQuery: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setIsLoading(true);

    try {
      const response: ChatResponse = await sendChatMessage({
        audio_base64: audioBase64,
        source_language: selectedLanguage,
        user_profile: 'general',
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
          regionalResponse: `त्रुटि (Error): ${err.message || 'Speech processing failed.'}`,
          englishResponse: `Error: ${err.message || 'Speech processing failed.'}`,
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
      setAttachedDoc(null);
    }
  };

  return (
    <div className={`flex flex-col h-[750px] bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden ${className}`}>
      {/* Hidden File Input for Document Attachment */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        accept=".pdf,.docx,.doc,.txt"
        className="hidden"
      />

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
                Live GraphRAG
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
                    className="p-3 rounded-xl border border-gray-200 bg-white hover:border-primary-400 hover:bg-primary-50/50 text-left transition-all text-xs text-gray-700 shadow-2xs group"
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

                      {/* Rendered Markdown Response Body */}
                      <div className="text-sm text-gray-800 leading-relaxed space-y-2.5">
                        <ReactMarkdown
                          components={{
                            h3: ({ node, ...props }) => (
                              <h3 className="text-sm font-bold text-primary-900 mt-3 mb-1 border-b border-gray-100 pb-1" {...props} />
                            ),
                            h4: ({ node, ...props }) => (
                              <h4 className="text-xs font-bold text-gray-800 mt-2 mb-0.5" {...props} />
                            ),
                            strong: ({ node, ...props }) => (
                              <strong className="font-semibold text-primary-950" {...props} />
                            ),
                            ul: ({ node, ...props }) => (
                              <ul className="list-disc list-inside space-y-1 my-1.5 pl-1" {...props} />
                            ),
                            ol: ({ node, ...props }) => (
                              <ol className="list-decimal list-inside space-y-1 my-1.5 pl-1" {...props} />
                            ),
                            li: ({ node, ...props }) => (
                              <li className="text-xs text-gray-700" {...props} />
                            ),
                            p: ({ node, ...props }) => (
                              <p className="text-xs leading-relaxed text-gray-700" {...props} />
                            ),
                            blockquote: ({ node, ...props }) => (
                              <blockquote className="border-l-2 border-primary-400 pl-3 italic text-gray-600 text-xs my-2" {...props} />
                            ),
                          }}
                        >
                          {displayText}
                        </ReactMarkdown>
                      </div>

                      {/* Voice Audio Readout Player (Web Speech + WAV) */}
                      <div className="mt-2 pt-2 border-t border-gray-100">
                        <AudioPlayer
                          textToSpeak={displayText}
                          language={currentLang === 'english' ? 'en' : selectedLanguage}
                          audioBase64={msg.audioBase64}
                        />
                      </div>

                      {/* Citations Card */}
                      {msg.citations && msg.citations.length > 0 && (
                        <CitationCard citations={msg.citations} />
                      )}

                      {/* Timestamp & Legal Aid banner */}
                      <div className="flex items-center justify-between pt-1 text-[10px] text-gray-400">
                        <span className="flex items-center gap-1 text-amber-700 font-medium">
                          <PhoneCall className="w-3 h-3" />
                          National Legal Aid: 15100 (Toll-Free, 24x7)
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
                  Analyzing legal statutes & traversing Neo4j knowledge graph...
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
        {/* Document Attached Pill */}
        {attachedDoc && (
          <div className="flex items-center justify-between bg-primary-50 border border-primary-200 rounded-xl px-3 py-1.5 text-xs text-primary-900">
            <div className="flex items-center gap-2 truncate">
              <FileText className="w-4 h-4 text-primary-600 flex-shrink-0" />
              <span className="font-semibold truncate">{attachedDoc.filename}</span>
              <span className="text-[11px] bg-primary-200/80 text-primary-800 px-2 py-0.5 rounded-full flex-shrink-0">
                {attachedDoc.chunks_created} chunks in Neo4j
              </span>
            </div>
            <button
              type="button"
              onClick={removeAttachedDoc}
              className="text-gray-400 hover:text-red-600 p-0.5 transition-colors"
              title="Remove document context"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Uploading Spinner */}
        {isUploadingDoc && (
          <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-xl px-3 py-1.5 text-xs text-blue-700 animate-pulse">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Uploading & indexing legal document into Neo4j GraphRAG...</span>
          </div>
        )}

        {/* Live Speech Recognition Banner */}
        {isListening && (
          <div className="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-xl px-4 py-2 animate-pulse">
            <div className="flex items-center gap-2 text-amber-900 text-xs font-medium">
              <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-ping" />
              <span>{t.listening}</span>
              {speechInterim && (
                <span className="italic text-gray-600 font-normal">"{speechInterim}"</span>
              )}
            </div>
            <button
              type="button"
              onClick={stopListening}
              className="flex items-center gap-1 text-xs font-bold bg-amber-600 text-white px-3 py-1 rounded-lg hover:bg-amber-700"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              {t.stopSend}
            </button>
          </div>
        )}

        {/* MediaRecorder Fallback banner */}
        {isMediaRecording && (
          <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-xl px-4 py-2 animate-pulse">
            <div className="flex items-center gap-2 text-red-700 text-xs font-semibold">
              <span className="w-2.5 h-2.5 rounded-full bg-red-600" />
              {t.listening} ({recordDuration}s)
            </div>
            <button
              type="button"
              onClick={stopMediaRecording}
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
          {/* File Attachment Button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading || isUploadingDoc}
            className="p-3 rounded-xl border-2 border-gray-200 text-gray-500 hover:border-primary-500 hover:text-primary-600 hover:bg-primary-50 transition-all flex-shrink-0 disabled:opacity-50"
            title={t.attachDoc}
            aria-label="Attach legal document PDF or Word"
          >
            <Paperclip className="w-5 h-5" />
          </button>

          {/* Microphone button with Live Web Speech Recognition */}
          <button
            type="button"
            onClick={toggleListening}
            disabled={isLoading}
            className={`p-3 rounded-xl border-2 transition-all flex-shrink-0 flex items-center justify-center ${
              isListening || isMediaRecording
                ? 'border-red-500 bg-red-500 text-white animate-bounce'
                : 'border-gray-200 text-gray-600 hover:border-primary-500 hover:text-primary-600 hover:bg-primary-50'
            } disabled:opacity-50`}
            title={isListening ? t.stopSend : 'Speak query in your language (बोलकर पूछें)'}
            aria-label="Microphone record button"
          >
            <Mic className="w-5 h-5" />
          </button>

          {/* Text Input */}
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={isListening ? 'Listening...' : t.inputPlaceholder}
            disabled={isLoading}
            className="flex-1 px-4 py-3 bg-gray-50 border-2 border-gray-200 rounded-xl text-sm text-gray-900 focus:bg-white focus:border-primary-500 focus:ring-4 focus:ring-primary-100 outline-none transition-all placeholder:text-gray-400 disabled:opacity-50"
          />

          {/* Send Button */}
          <button
            type="submit"
            disabled={isLoading || !inputText.trim()}
            className="p-3 bg-primary-600 hover:bg-primary-700 active:scale-95 text-white rounded-xl font-medium transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
            aria-label="Send query"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>

        <div className="flex items-center justify-between text-[11px] text-gray-400 px-1">
          <span>Supported: Voice, Text & PDF reports in 14 Indian languages</span>
          <span>Legal Aid Toll-Free: 15100</span>
        </div>
      </div>
    </div>
  );
}

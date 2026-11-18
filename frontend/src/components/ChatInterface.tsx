'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
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
  History,
  Plus,
  MessageSquare,
  Lock,
  LogIn,
  Clock,
  ChevronLeft,
  ChevronRight,
  Shield,
} from 'lucide-react';
import {
  sendChatMessage,
  uploadDocument,
  translateLegalText,
  getUserThreads,
  getThreadMessages,
  deleteThread,
  MessageItem,
  ChatResponse,
  UploadResponse,
  UserInfo,
  ConsultationThread,
  ThreadMessageItem,
} from '@/lib/api';
import { getUITranslations } from '@/lib/i18n';
import { INDIAN_LANGUAGES } from './LanguageSelector';
import AudioPlayer from './AudioPlayer';
import CitationCard from './CitationCard';

interface ChatInterfaceProps {
  selectedLanguage: string;
  className?: string;
  currentUser?: UserInfo | null;
  onOpenAuthModal?: () => void;
}

export default function ChatInterface({
  selectedLanguage,
  className = '',
  currentUser = null,
  onOpenAuthModal,
}: ChatInterfaceProps) {
  const t = getUITranslations(selectedLanguage);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Consultation Threads & History State
  const [threads, setThreads] = useState<ConsultationThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [isLoadingThreads, setIsLoadingThreads] = useState(false);
  const [showHistorySidebar, setShowHistorySidebar] = useState(true);

  // Per-message active language tracking: { [messageId]: 'bn' | 'hi' | 'en' | ... }
  const [messageLanguages, setMessageLanguages] = useState<Record<string, string>>({});
  // Per-message cached translations: { [messageId]: { [langCode]: { text: string, audioBase64?: string } } }
  const [cachedTranslations, setCachedTranslations] = useState<
    Record<string, Record<string, { text: string; audioBase64?: string | null }>>
  >({});
  const [translatingMsgId, setTranslatingMsgId] = useState<string | null>(null);

  // Document Attachment State in Chat
  const [isUploadingDoc, setIsUploadingDoc] = useState(false);
  const [attachedDoc, setAttachedDoc] = useState<UploadResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Voice recording via MediaRecorder (universal multimodal recording)
  const [isRecording, setIsRecording] = useState(false);
  const [recordDuration, setRecordDuration] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordTimerRef = useRef<NodeJS.Timeout | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // -------------------------------------------------------------
  // Load User Consultation Threads
  // -------------------------------------------------------------
  const loadUserThreads = useCallback(async () => {
    if (!currentUser) {
      setThreads([]);
      return;
    }
    setIsLoadingThreads(true);
    try {
      const userThreads = await getUserThreads();
      setThreads(userThreads);
    } catch {
      setThreads([]);
    } finally {
      setIsLoadingThreads(false);
    }
  }, [currentUser]);

  useEffect(() => {
    loadUserThreads();
  }, [loadUserThreads]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, isRecording]);

  // Clean up timers on unmount
  useEffect(() => {
    return () => {
      if (recordTimerRef.current) clearInterval(recordTimerRef.current);
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stop();
      }
    };
  }, [isRecording]);

  const handleCopyText = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // -------------------------------------------------------------
  // Consultation Thread Actions: New Thread & Load Thread
  // -------------------------------------------------------------
  const startNewConsultation = () => {
    setActiveThreadId(null);
    setMessages([]);
    setAttachedDoc(null);
  };

  const handleSelectThread = async (threadId: string) => {
    if (activeThreadId === threadId || isLoading) return;
    setIsLoading(true);
    try {
      const rawMessages: ThreadMessageItem[] = await getThreadMessages(threadId);
      setActiveThreadId(threadId);
      setAttachedDoc(null);

      const formattedMessages: MessageItem[] = rawMessages.map((m) => {
        const timestamp = m.created_at
          ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          : '';
        return {
          id: m.id,
          sender: m.sender as 'user' | 'assistant',
          originalQuery: m.original_query || undefined,
          englishQuery: m.english_query || undefined,
          regionalResponse: m.regional_response || undefined,
          englishResponse: m.english_response || undefined,
          citations: m.citations || [],
          audioBase64: m.audio_base64 || null,
          detectedLanguage: m.detected_language || 'hi',
          timestamp,
        };
      });

      // Update message languages and translation cache
      const newLanguages: Record<string, string> = {};
      const newCache: Record<string, Record<string, { text: string; audioBase64?: string | null }>> = {};

      formattedMessages.forEach((msg) => {
        if (msg.sender === 'assistant') {
          const lang = msg.detectedLanguage || 'hi';
          newLanguages[msg.id] = lang;
          newCache[msg.id] = {
            [lang]: {
              text: msg.regionalResponse || msg.englishResponse || '',
              audioBase64: msg.audioBase64,
            },
            ...(msg.englishResponse ? { en: { text: msg.englishResponse, audioBase64: null } } : {}),
          };
        }
      });

      setMessageLanguages(newLanguages);
      setCachedTranslations(newCache);
      setMessages(formattedMessages);
    } catch (err: any) {
      alert(`Could not load consultation thread: ${err.message || 'Error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteThread = async (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this consultation history? This action is permanent.')) {
      return;
    }
    try {
      await deleteThread(threadId);
      if (activeThreadId === threadId) {
        startNewConsultation();
      }
      await loadUserThreads();
    } catch (err: any) {
      alert(`Failed to delete consultation: ${err.message || 'Error'}`);
    }
  };

  // -------------------------------------------------------------
  // Dynamic Language & Audio Switcher per Response Message
  // -------------------------------------------------------------
  const handleSwitchMessageLanguage = async (msg: MessageItem, targetLang: string) => {
    if (translatingMsgId) return;
    const currentLang = messageLanguages[msg.id] || msg.detectedLanguage || selectedLanguage;
    if (currentLang === targetLang) return;

    // Check if translation is already cached in memory
    const cached = cachedTranslations[msg.id]?.[targetLang];
    if (cached) {
      setMessageLanguages((prev) => ({ ...prev, [msg.id]: targetLang }));
      return;
    }

    setTranslatingMsgId(msg.id);
    try {
      const sourceText = msg.englishResponse || msg.regionalResponse || '';
      const sourceLang = msg.englishResponse ? 'en' : currentLang;

      const res = await translateLegalText(sourceText, targetLang, sourceLang);

      setCachedTranslations((prev) => ({
        ...prev,
        [msg.id]: {
          ...(prev[msg.id] || {}),
          [targetLang]: {
            text: res.translated_text,
            audioBase64: res.audio_base64,
          },
        },
      }));
      setMessageLanguages((prev) => ({ ...prev, [msg.id]: targetLang }));
    } catch (err: any) {
      alert(`Could not translate response to selected language: ${err.message || 'Network error'}`);
    } finally {
      setTranslatingMsgId(null);
    }
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
  // Send Text Chat Message
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
    setIsLoading(true);

    try {
      const response: ChatResponse = await sendChatMessage({
        text,
        source_language: selectedLanguage,
        user_profile: 'general',
        thread_id: activeThreadId || undefined,
      });

      if (response.thread_id && response.thread_id !== activeThreadId) {
        setActiveThreadId(response.thread_id);
      }

      const assistantMessageId = 'resp-' + Date.now();
      const detectedLang = response.detected_language || selectedLanguage;

      const newAssistantMessage: MessageItem = {
        id: assistantMessageId,
        sender: 'assistant',
        originalQuery: response.original_query,
        englishQuery: response.english_query,
        regionalResponse: response.regional_response,
        englishResponse: response.english_response,
        citations: response.citations,
        audioBase64: response.audio_base64,
        detectedLanguage: detectedLang,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, newAssistantMessage]);
      setMessageLanguages((prev) => ({
        ...prev,
        [assistantMessageId]: detectedLang,
      }));

      // Pre-populate translation cache with initial responses
      setCachedTranslations((prev) => ({
        ...prev,
        [assistantMessageId]: {
          [detectedLang]: {
            text: response.regional_response,
            audioBase64: response.audio_base64,
          },
          ...(response.english_response
            ? { en: { text: response.english_response, audioBase64: null } }
            : {}),
        },
      }));

      // Refresh consultation threads list for logged-in user
      if (currentUser) {
        loadUserThreads();
      }
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
  // Automatic Audio Recognition & Multimodal Speech Recording
  // -------------------------------------------------------------
  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const startRecording = async () => {
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
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

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
    } catch {
      alert('Microphone access is required for voice queries. Please grant microphone permission in your browser.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (recordTimerRef.current) clearInterval(recordTimerRef.current);
    }
  };

  const handleSendAudioMessage = async (audioBase64: string) => {
    const userMessageId = 'msg-audio-' + Date.now();
    const newUserMessage: MessageItem = {
      id: userMessageId,
      sender: 'user',
      originalQuery: '🎤 [ऑडियो विश्लेषण हो रहा है... / Transcribing audio query...]',
      isAudioQuery: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setIsLoading(true);

    try {
      const response: ChatResponse = await sendChatMessage({
        audio_base64: audioBase64,
        source_language: 'auto', // Request automatic audio language identification
        user_profile: 'general',
        thread_id: activeThreadId || undefined,
      });

      if (response.thread_id && response.thread_id !== activeThreadId) {
        setActiveThreadId(response.thread_id);
      }

      // Update user message with the recognized spoken words in native script
      setMessages((prev) =>
        prev.map((m) =>
          m.id === userMessageId
            ? { ...m, originalQuery: response.original_query }
            : m
        )
      );

      const assistantMessageId = 'resp-' + Date.now();
      const detectedLang = response.detected_language || 'hi';

      const newAssistantMessage: MessageItem = {
        id: assistantMessageId,
        sender: 'assistant',
        originalQuery: response.original_query,
        englishQuery: response.english_query,
        regionalResponse: response.regional_response,
        englishResponse: response.english_response,
        citations: response.citations,
        audioBase64: response.audio_base64,
        detectedLanguage: detectedLang,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, newAssistantMessage]);
      setMessageLanguages((prev) => ({
        ...prev,
        [assistantMessageId]: detectedLang,
      }));

      // Cache initial native language response and English fallback
      setCachedTranslations((prev) => ({
        ...prev,
        [assistantMessageId]: {
          [detectedLang]: {
            text: response.regional_response,
            audioBase64: response.audio_base64,
          },
          ...(response.english_response
            ? { en: { text: response.english_response, audioBase64: null } }
            : {}),
        },
      }));

      // Refresh consultation threads for logged-in user
      if (currentUser) {
        loadUserThreads();
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: 'err-' + Date.now(),
          sender: 'assistant',
          regionalResponse: `त्रुटि (Error): ${err.message || 'Speech recognition failed.'}`,
          englishResponse: `Error: ${err.message || 'Speech recognition failed.'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    if (confirm('Clear the current legal consultation conversation?')) {
      startNewConsultation();
    }
  };

  const activeThread = threads.find((t) => t.id === activeThreadId);

  return (
    <div className={`flex h-[750px] bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden ${className}`}>
      {/* Hidden File Input for PDF/Doc Upload */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        accept=".pdf,.docx,.doc,.txt"
        className="hidden"
      />

      {/* --------------------------------------------------------- */}
      {/* LEFT PANE: Recent Chat History & Consultation Threads     */}
      {/* --------------------------------------------------------- */}
      {showHistorySidebar && (
        <aside className="w-72 sm:w-80 border-r border-gray-200 bg-slate-50/90 flex flex-col shrink-0 transition-all duration-200 h-full">
          {/* Sidebar Top: Action & Title */}
          <div className="p-3.5 border-b border-gray-200 bg-white/80 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-primary-700" />
              <span className="font-bold text-xs text-gray-800 tracking-tight">
                परामर्श इतिहास (History)
              </span>
            </div>
            <button
              type="button"
              onClick={() => setShowHistorySidebar(false)}
              className="p-1 text-gray-400 hover:text-gray-600 rounded-lg lg:hidden"
              title="Close history sidebar"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          </div>

          {/* New Consultation Button */}
          <div className="p-3">
            <button
              type="button"
              onClick={startNewConsultation}
              className="w-full py-2 px-3 bg-primary-700 hover:bg-primary-800 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-xs transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>+ नया परामर्श (+ New Consultation)</span>
            </button>
          </div>

          {/* Threads List / Auth Prompt */}
          <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1.5">
            {!currentUser ? (
              <div className="p-4 bg-white border border-gray-200 rounded-2xl text-center space-y-3 mt-4 shadow-2xs">
                <div className="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center text-primary-700 mx-auto">
                  <Lock className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-gray-900">
                    निजी परामर्श इतिहास
                  </h4>
                  <p className="text-[11px] text-gray-500 mt-1 leading-relaxed">
                    अपने कानूनी परामर्श को सुरक्षित सहेजने और बाद में देखने के लिए लॉग इन करें। आपका डेटा पूरी तरह निजी है।
                  </p>
                </div>
                <button
                  type="button"
                  onClick={onOpenAuthModal}
                  className="w-full py-2 px-3 bg-accent-500 hover:bg-accent-600 text-white text-xs font-bold rounded-xl shadow-xs transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  Log In / Sign Up
                </button>
              </div>
            ) : isLoadingThreads ? (
              <div className="flex items-center justify-center p-6 text-gray-400 gap-2 text-xs">
                <Loader2 className="w-4 h-4 animate-spin text-primary-600" />
                <span>परामर्श लोड हो रहे हैं...</span>
              </div>
            ) : threads.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-6 text-center text-gray-400 space-y-2 my-auto">
                <MessageSquare className="w-8 h-8 text-gray-300 stroke-[1.5]" />
                <p className="text-xs font-medium text-gray-600">कोई पुराना परामर्श नहीं</p>
                <p className="text-[11px] text-gray-400">
                  कानूनी प्रश्न पूछकर नया परामर्श शुरू करें।
                </p>
              </div>
            ) : (
              threads.map((th) => {
                const isActive = activeThreadId === th.id;
                const formattedDate = th.updated_at
                  ? new Date(th.updated_at).toLocaleDateString([], { month: 'short', day: 'numeric' })
                  : '';
                return (
                  <div
                    key={th.id}
                    onClick={() => handleSelectThread(th.id)}
                    className={`group relative p-2.5 rounded-xl border text-xs cursor-pointer transition-all flex items-start justify-between gap-2 ${
                      isActive
                        ? 'bg-primary-50/90 border-primary-300 text-primary-950 font-semibold shadow-2xs'
                        : 'bg-white border-gray-200/80 hover:bg-gray-50 text-gray-700'
                    }`}
                  >
                    <div className="flex items-start gap-2 min-w-0 flex-1">
                      <MessageSquare className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${isActive ? 'text-primary-600' : 'text-gray-400'}`} />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-medium text-gray-900 group-hover:text-primary-700">
                          {th.title}
                        </p>
                        <div className="flex items-center gap-2 text-[10px] text-gray-400 mt-1">
                          <span className="flex items-center gap-1">
                            <Clock className="w-2.5 h-2.5" /> {formattedDate}
                          </span>
                          <span>•</span>
                          <span>{th.message_count} संदेश</span>
                        </div>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => handleDeleteThread(e, th.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-all shrink-0"
                      title="Delete this consultation"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })
            )}
          </div>

          {currentUser && (
            <div className="p-3 border-t border-gray-200 bg-white/60 text-[10px] text-gray-500 flex items-center justify-between">
              <span className="truncate">👤 {currentUser.full_name}</span>
              <span className="text-primary-700 font-semibold">निजी डेटा सुरक्षित</span>
            </div>
          )}
        </aside>
      )}

      {/* --------------------------------------------------------- */}
      {/* RIGHT PANE: Chat View & Message Stream                    */}
      {/* --------------------------------------------------------- */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-white">
        {/* Chat Header */}
        <div className="px-4 py-3 bg-gradient-to-r from-primary-900 to-primary-800 text-white flex items-center justify-between border-b border-primary-700">
          <div className="flex items-center gap-3">
            {/* Sidebar Toggle Button */}
            <button
              type="button"
              onClick={() => setShowHistorySidebar((prev) => !prev)}
              className="p-1.5 rounded-lg bg-primary-800/80 hover:bg-primary-700 text-gray-200 hover:text-white transition-colors flex items-center gap-1.5 text-xs font-medium"
              title={showHistorySidebar ? 'Hide Consultations History' : 'View Recent Consultations History'}
            >
              <History className="w-4 h-4 text-accent-300" />
              <span className="hidden sm:inline">
                {showHistorySidebar ? 'परामर्श छुपाएं' : 'परामर्श इतिहास'}
              </span>
              {threads.length > 0 && (
                <span className="bg-accent-500 text-white text-[10px] px-1.5 py-0.2 rounded-full font-bold">
                  {threads.length}
                </span>
              )}
            </button>

            <div className="w-8 h-8 rounded-xl bg-accent-500/20 border border-accent-400/30 flex items-center justify-center text-accent-300 shrink-0">
              <Scale className="w-4 h-4" />
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="text-xs sm:text-sm font-bold tracking-tight truncate">
                  {activeThread ? activeThread.title : t.chatHeader}
                </h2>
                <span className="hidden sm:inline bg-accent-500/30 text-accent-200 text-[10px] font-semibold px-2 py-0.5 rounded-full border border-accent-400/20 shrink-0">
                  Live GraphRAG
                </span>
              </div>
              <p className="text-[10px] sm:text-[11px] text-gray-300 truncate">
                {activeThread ? `Active Thread: ${activeThread.id}` : t.chatSubtitle}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button
                type="button"
                onClick={clearChat}
                className="p-1.5 text-gray-300 hover:text-red-300 hover:bg-primary-800/80 rounded-lg transition-colors flex items-center gap-1 text-xs"
                title="Clear current consultation"
                aria-label="Clear chat"
              >
                <Trash2 className="w-4 h-4" />
                <span className="hidden md:inline">हटाएं (Clear)</span>
              </button>
            )}
          </div>
        </div>

        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4 bg-slate-50/60">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
              <div className="w-16 h-16 rounded-3xl bg-primary-100 flex items-center justify-center text-primary-700 shadow-inner">
                <Sparkles className="w-8 h-8" />
              </div>

              <div className="max-w-md space-y-1">
                <h3 className="text-lg font-bold text-gray-900">
                  {t.chatGreeting}
                </h3>
                <p className="text-xs text-gray-500 leading-relaxed">
                  {t.chatGreetingSub}
                </p>
              </div>

              {/* Quick Suggested Queries */}
              <div className="w-full max-w-xl text-left space-y-2 pt-2">
                <p className="text-[11px] font-bold text-gray-400 uppercase tracking-wider text-center">
                  {t.suggestedQueriesTitle}
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {t.suggestedQueries.map((query, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleSendMessage(query.text)}
                      disabled={isLoading}
                      className="p-3 bg-white hover:bg-primary-50/70 border border-gray-200 hover:border-primary-300 rounded-xl text-left transition-all group shadow-2xs flex flex-col justify-between cursor-pointer"
                    >
                      <span className="text-xs font-semibold text-primary-900 group-hover:text-primary-700">
                        {query.label}
                      </span>
                      <span className="text-[11px] text-gray-500 line-clamp-1 mt-1">
                        "{query.text}"
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            messages.map((msg) => {
              const isUser = msg.sender === 'user';
              const activeLang = messageLanguages[msg.id] || msg.detectedLanguage || selectedLanguage;
              const currentTranslation = cachedTranslations[msg.id]?.[activeLang];
              const displayText = isUser
                ? msg.originalQuery || ''
                : currentTranslation?.text || msg.regionalResponse || msg.englishResponse || '';
              const activeAudio = isUser
                ? null
                : currentTranslation?.audioBase64 || msg.audioBase64;

              return (
                <div
                  key={msg.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[88%] md:max-w-[80%] rounded-2xl p-4 shadow-xs ${
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
                        {/* Assistant Header & Dynamic Regional Language Switcher */}
                        <div className="flex items-center justify-between border-b border-gray-100 pb-2 gap-2 flex-wrap">
                          <div className="flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-primary-600" />
                            <span className="text-xs font-bold text-primary-900">
                              Nyayavarta Legal Guidance
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            {/* Regional Language & Audio Switcher Dropdown */}
                            <div className="flex items-center gap-1 bg-primary-50 border border-primary-200 rounded-lg px-2 py-0.5 shadow-2xs">
                              <Languages className="w-3.5 h-3.5 text-primary-600 flex-shrink-0" />
                              <select
                                value={activeLang}
                                onChange={(e) => handleSwitchMessageLanguage(msg, e.target.value)}
                                disabled={translatingMsgId === msg.id}
                                className="bg-transparent text-[11px] font-semibold text-primary-900 outline-none cursor-pointer"
                                title="Change answer language and voice audio to any regional language of India"
                              >
                                {INDIAN_LANGUAGES.map((l) => (
                                  <option key={l.code} value={l.code} className="text-gray-900">
                                    {l.nativeName} ({l.name})
                                  </option>
                                ))}
                              </select>
                              {translatingMsgId === msg.id && (
                                <Loader2 className="w-3 h-3 text-primary-600 animate-spin ml-1" />
                              )}
                            </div>

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

                        {/* Markdown Formatted Legal Advice */}
                        <div className="prose prose-sm max-w-none text-gray-800 text-xs sm:text-sm leading-relaxed">
                          <ReactMarkdown>{displayText}</ReactMarkdown>
                        </div>

                        {/* Audio Player for Spoken Voice Advice */}
                        <AudioPlayer
                          audioBase64={activeAudio}
                          language={activeLang}
                          textToSpeak={displayText}
                        />

                        {/* Legal Citations & Law Transition Matrix */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="pt-2">
                            <CitationCard citations={msg.citations} />
                          </div>
                        )}

                        <div className="flex items-center justify-between pt-2 border-t border-gray-100 text-[10px] text-gray-400">
                          <span className="flex items-center gap-1">
                            <PhoneCall className="w-3 h-3 text-accent-500" />
                            {t.emergencyTitle}: 15100 (Toll-Free, 24x7)
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
                    Retrieving BNS/BNSS/BSA law transitions with Gemini Multimodal AI
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

          {/* Live Audio Recording Badge */}
          {isRecording && (
            <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-xl px-4 py-2 animate-pulse">
              <div className="flex items-center gap-2 text-red-700 text-xs font-semibold">
                <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-ping" />
                <span>ऑडियो रिकॉर्ड हो रहा है (Speak in any Indian language: Bengali, Hindi, Tamil...)... {recordDuration}s</span>
              </div>
              <button
                type="button"
                onClick={stopRecording}
                className="flex items-center gap-1 text-xs font-bold bg-red-600 text-white px-3 py-1 rounded-lg hover:bg-red-700 cursor-pointer"
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
              className="p-3 rounded-xl border-2 border-gray-200 text-gray-500 hover:border-primary-500 hover:text-primary-600 hover:bg-primary-50 transition-all flex-shrink-0 disabled:opacity-50 cursor-pointer"
              title={t.attachDoc}
              aria-label="Attach legal document PDF or Word"
            >
              <Paperclip className="w-5 h-5" />
            </button>

            {/* Microphone button with Automatic Language Recognition */}
            <button
              type="button"
              onClick={toggleRecording}
              disabled={isLoading}
              className={`p-3 rounded-xl border-2 transition-all flex-shrink-0 flex items-center justify-center cursor-pointer ${
                isRecording
                  ? 'border-red-500 bg-red-500 text-white animate-bounce'
                  : 'border-gray-200 text-gray-600 hover:border-primary-500 hover:text-primary-600 hover:bg-primary-50'
              } disabled:opacity-50`}
              title={isRecording ? t.stopSend : 'Speak query in any Indian language (बोलकर पूछें - स्वचालित भाषा पहचान)'}
              aria-label="Microphone record button"
            >
              <Mic className="w-5 h-5" />
            </button>

            {/* Text Input */}
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={isRecording ? 'Listening in any language...' : t.inputPlaceholder}
              disabled={isLoading}
              className="flex-1 px-4 py-3 bg-gray-50 border-2 border-gray-200 rounded-xl text-sm text-gray-900 focus:bg-white focus:border-primary-500 focus:ring-4 focus:ring-primary-100 outline-none transition-all placeholder:text-gray-400 disabled:opacity-50"
            />

            {/* Send Button */}
            <button
              type="submit"
              disabled={isLoading || !inputText.trim()}
              className="p-3 bg-primary-600 hover:bg-primary-700 active:scale-95 text-white rounded-xl font-medium transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0 cursor-pointer"
              aria-label="Send query"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>

          <div className="flex items-center justify-between text-[11px] text-gray-400 px-1">
            <span>Supported: Automatic Voice Detection, Text & PDF reports in 14 Indian languages</span>
            <span>Legal Aid Toll-Free: 15100</span>
          </div>
        </div>
      </div>
    </div>
  );
}

'use client';

import React, { useState, useEffect } from 'react';
import {
  Scale,
  MessageSquare,
  Upload,
  BookOpen,
  PhoneCall,
  ShieldCheck,
  CheckCircle2,
  ExternalLink,
  ArrowRight,
  FileText,
  User,
  LogOut,
} from 'lucide-react';
import LanguageSelector from '@/components/LanguageSelector';
import ChatInterface from '@/components/ChatInterface';
import DocumentUpload from '@/components/DocumentUpload';
import LawMatrix from '@/components/LawMatrix';
import AuthModal from '@/components/AuthModal';
import { checkHealth, UploadResponse, getCurrentUser, logoutUser, UserInfo } from '@/lib/api';
import { getUITranslations } from '@/lib/i18n';

export default function Home() {
  const [selectedLanguage, setSelectedLanguage] = useState('en');
  const [activeTab, setActiveTab] = useState<'chat' | 'upload' | 'reference'>('chat');
  const [backendStatus, setBackendStatus] = useState<'checking' | 'healthy' | 'offline'>('checking');
  const [uploadedFiles, setUploadedFiles] = useState<UploadResponse[]>([]);
  const [activeDocument, setActiveDocument] = useState<UploadResponse | null>(null);
  const [initialChatQuery, setInitialChatQuery] = useState<string | null>(null);

  // User Authentication State
  const [currentUser, setCurrentUser] = useState<UserInfo | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const t = getUITranslations(selectedLanguage);

  useEffect(() => {
    checkHealth()
      .then((res) => {
        if (res.status === 'healthy') setBackendStatus('healthy');
        else setBackendStatus('offline');
      })
      .catch(() => setBackendStatus('offline'));

    // Check for existing user session
    getCurrentUser()
      .then((user) => setCurrentUser(user))
      .catch(() => setCurrentUser(null));
  }, []);

  // Isolate and persist uploaded documents per authenticated user
  useEffect(() => {
    if (currentUser?.id) {
      try {
        const stored = localStorage.getItem(`nyayavarta_docs_${currentUser.id}`);
        if (stored) {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed)) {
            setUploadedFiles(parsed);
          } else {
            setUploadedFiles([]);
          }
        } else {
          setUploadedFiles([]);
        }
      } catch {
        setUploadedFiles([]);
      }
    } else {
      // Clear files completely when logged out / in guest mode
      setUploadedFiles([]);
      setActiveDocument(null);
    }
  }, [currentUser]);

  const handleDocumentUploaded = (res: UploadResponse) => {
    setUploadedFiles((prev) => {
      const exists = prev.some((f) => f.filename === res.filename);
      const updated = exists ? prev : [res, ...prev];
      if (currentUser?.id) {
        try {
          localStorage.setItem(`nyayavarta_docs_${currentUser.id}`, JSON.stringify(updated));
        } catch {
          // ignore
        }
      }
      return updated;
    });
    setActiveDocument(res);
  };

  const handleDocumentRemoved = () => {
    setActiveDocument(null);
  };

  const handleMatrixSelectQuery = (queryText: string) => {
    setInitialChatQuery(queryText);
    setActiveTab('chat');
  };

  const handleLogout = async () => {
    try {
      await logoutUser();
    } catch {
      // ignore
    }
    setCurrentUser(null);
    setUploadedFiles([]);
    setActiveDocument(null);
    setInitialChatQuery(null);
  };

  return (
    <div className="min-h-screen bg-slate-50/70 text-slate-900 flex flex-col font-sans">
      {/* Top Banner / Emergency Legal Aid Bar */}
      <div className="bg-[#0b0f19] text-slate-300 text-xs px-4 py-2 border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="bg-amber-500/15 text-amber-300 border border-amber-500/30 text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
              {t.emergencyTitle}
            </span>
            <span className="font-medium text-slate-300">
              {t.legalAidText}
            </span>
            <a
              href="tel:15100"
              className="font-bold text-amber-300 hover:text-amber-200 underline inline-flex items-center gap-1 ml-1"
            >
              <PhoneCall className="w-3 h-3" /> {t.tollFree}
            </a>
          </div>

          <div className="flex items-center gap-4 text-slate-400 text-[11px]">
            <span className="hover:text-slate-200 transition-colors">{t.police}</span>
            <span className="hover:text-slate-200 transition-colors">{t.cyberCrime}</span>
            <span className="hover:text-slate-200 transition-colors">{t.women}</span>
          </div>
        </div>
      </div>

      {/* Main Header */}
      <header className="bg-white/90 backdrop-blur-md border-b border-slate-200/90 shadow-xs sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
          {/* Logo & Title */}
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-850 to-slate-950 flex items-center justify-center text-amber-400 shadow-sm ring-1 ring-slate-800/20">
              <Scale className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">
                  {t.appTitle}
                </h1>
                <span className="text-xs font-semibold text-slate-300">|</span>
                <span className="text-sm font-semibold text-slate-700 tracking-tight">
                  Nyayavarta
                </span>
                <span className="hidden sm:inline-flex items-center gap-1.5 bg-emerald-50 text-emerald-700 text-[10px] font-semibold px-2.5 py-0.5 rounded-full border border-emerald-200/80">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  {backendStatus === 'healthy' ? t.apiOnline : 'Active'}
                </span>
              </div>
              <p className="text-xs text-slate-500 font-normal">
                {t.appSubtitle}
              </p>
            </div>
          </div>

          {/* Controls: User Auth & Language Selector */}
          <div className="flex items-center gap-3">
            {currentUser ? (
              <div className="flex items-center gap-2 bg-slate-100 border border-slate-200/90 py-1.5 px-3 rounded-xl shadow-2xs">
                <div className="w-6 h-6 rounded-lg bg-slate-900 text-white flex items-center justify-center text-xs font-bold">
                  {currentUser.full_name.charAt(0).toUpperCase()}
                </div>
                <span className="text-xs font-semibold text-slate-900 max-w-[120px] truncate">
                  {currentUser.full_name}
                </span>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="p-1 text-slate-400 hover:text-red-600 rounded transition-colors ml-1 cursor-pointer"
                  title={t.userLogOutBtn}
                  aria-label={t.userLogOutBtn}
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setIsAuthModalOpen(true)}
                className="flex items-center gap-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold py-2 px-3.5 rounded-xl shadow-xs transition-all cursor-pointer"
              >
                <User className="w-3.5 h-3.5 text-amber-400" />
                <span>{t.userLoginBtn}</span>
              </button>
            )}

            <LanguageSelector
              selectedLanguage={selectedLanguage}
              onLanguageChange={setSelectedLanguage}
            />
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full space-y-6">
        {/* Navigation Tabs */}
        <div className="flex items-center justify-between border-b border-slate-200/90">
          <nav className="flex space-x-2 sm:space-x-3">
            <button
              type="button"
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2 py-3 px-4 font-semibold text-xs sm:text-sm border-b-2 transition-all cursor-pointer ${
                activeTab === 'chat'
                  ? 'border-slate-900 text-slate-950 bg-slate-100/60 rounded-t-xl'
                  : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              {t.tabChat}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('upload')}
              className={`flex items-center gap-2 py-3 px-4 font-semibold text-xs sm:text-sm border-b-2 transition-all cursor-pointer ${
                activeTab === 'upload'
                  ? 'border-slate-900 text-slate-950 bg-slate-100/60 rounded-t-xl'
                  : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
              }`}
            >
              <Upload className="w-4 h-4" />
              {t.tabUpload}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('reference')}
              className={`flex items-center gap-2 py-3 px-4 font-semibold text-xs sm:text-sm border-b-2 transition-all cursor-pointer ${
                activeTab === 'reference'
                  ? 'border-slate-900 text-slate-950 bg-slate-100/60 rounded-t-xl'
                  : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              {t.tabMatrix}
            </button>
          </nav>

          <div className="hidden md:flex items-center gap-2 text-xs text-slate-500">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>{t.ragTag}</span>
          </div>
        </div>

        {/* Tab 1: Chat Interface (Rendered continuously to preserve chat state across tab switches!) */}
        <div className={activeTab === 'chat' ? 'space-y-5' : 'hidden'}>
          <ChatInterface
            selectedLanguage={selectedLanguage}
            currentUser={currentUser}
            onOpenAuthModal={() => setIsAuthModalOpen(true)}
            attachedDoc={activeDocument}
            onDocumentUploaded={handleDocumentUploaded}
            onDocumentRemoved={handleDocumentRemoved}
            initialQuery={initialChatQuery}
            onClearInitialQuery={() => setInitialChatQuery(null)}
          />
        </div>

        {/* Tab 2: Document Upload & Knowledge Base (Kept mounted to preserve upload stats) */}
        <div className={activeTab === 'upload' ? 'space-y-6' : 'hidden'}>
          {/* Educational Explainer Banner */}
          <div className="bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 border border-slate-800 text-white rounded-2xl p-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="space-y-2 max-w-2xl">
              <div className="inline-flex items-center gap-1.5 bg-amber-500/15 text-amber-300 border border-amber-500/30 px-2.5 py-0.5 rounded-full text-xs font-semibold">
                <FileText className="w-3.5 h-3.5" />
                {t.uploadBannerTag}
              </div>
              <h3 className="text-lg font-bold text-slate-100">
                {t.uploadBannerTitle}
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                {t.uploadBannerDesc}
              </p>
            </div>

            <button
              type="button"
              onClick={() => setActiveTab('chat')}
              className="inline-flex items-center gap-2 bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold px-4 py-2.5 rounded-xl shadow transition-all whitespace-nowrap self-start md:self-auto cursor-pointer"
            >
              {t.goToChatBtn} <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <DocumentUpload
                selectedLanguage={selectedLanguage}
                onUploadSuccess={handleDocumentUploaded}
              />

              {/* Uploaded Documents History */}
              <div className="card">
                <h4 className="font-bold text-gray-800 text-sm mb-3 flex items-center justify-between">
                  <span>{t.indexedDocsTitle}</span>
                  <span className="text-xs font-normal text-gray-500">
                    {uploadedFiles.length} {t.filesCount}
                  </span>
                </h4>
                {uploadedFiles.length === 0 ? (
                  <p className="text-xs text-gray-400 italic">
                    {t.noDocsYet}
                  </p>
                ) : (
                  <div className="space-y-2">
                    {uploadedFiles.map((file, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-200 text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0" />
                          <span className="font-semibold text-gray-800">{file.filename}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="bg-primary-100 text-primary-800 px-2.5 py-0.5 rounded-full text-[11px] font-medium">
                            {file.chunks_created} {t.chunksInNeo4j}
                          </span>
                          <button
                            type="button"
                            onClick={() => {
                              setActiveDocument(file);
                              setActiveTab('chat');
                            }}
                            className="inline-flex items-center gap-1 bg-primary-600 hover:bg-primary-700 text-white text-[11px] font-semibold px-2.5 py-1 rounded-lg transition-colors cursor-pointer"
                          >
                            <span>{t.askInChat}</span>
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* RAG Knowledge Base Stats */}
            <div className="space-y-4">
              <div className="card bg-gradient-to-br from-primary-900 to-primary-950 text-white">
                <h4 className="font-bold text-sm mb-2 text-accent-300">
                  {t.architectureTitle}
                </h4>
                <p className="text-xs text-gray-300 leading-relaxed mb-4">
                  {t.architectureDesc}
                </p>
                <div className="space-y-2.5 text-xs">
                  <div className="flex justify-between pb-1.5 border-b border-white/10">
                    <span className="text-gray-300">{t.knowledgeGraphLabel}</span>
                    <span className="font-mono font-semibold text-white">Neo4j (Cypher Traversal)</span>
                  </div>
                  <div className="flex justify-between pb-1.5 border-b border-white/10">
                    <span className="text-gray-300">{t.keywordRetrievalLabel}</span>
                    <span className="font-mono font-semibold text-white">rank-bm25 (BM25Okapi)</span>
                  </div>
                  <div className="flex justify-between pb-1.5 border-b border-white/10">
                    <span className="text-gray-300">{t.orchestrationLabel}</span>
                    <span className="font-mono font-semibold text-accent-300">LangChain Neo4jGraph</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">{t.statutoryGraphDataLabel}</span>
                    <span className="font-mono font-semibold text-white">IPC/CrPC → BNS/BNSS/BSA</span>
                  </div>
                </div>
              </div>

              <div className="card">
                <h4 className="font-bold text-gray-800 text-sm mb-2">
                  {t.guidelinesTitle}
                </h4>
                <ul className="text-xs text-gray-600 space-y-2 list-disc list-inside">
                  <li>{t.guideline1}</li>
                  <li>{t.guideline2}</li>
                  <li>{t.guideline3}</li>
                  <li>{t.guideline4}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Tab 3: Law Transition Matrix & Landmark Precedents */}
        <div className={activeTab === 'reference' ? 'space-y-4' : 'hidden'}>
          <LawMatrix
            selectedLanguage={selectedLanguage}
            onSelectQuery={handleMatrixSelectQuery}
          />
        </div>
      </main>

      {/* Auth Modal for Log In / Sign Up */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={(user) => setCurrentUser(user)}
      />

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-gray-500">
          <div className="flex items-center gap-2">
            <span className="font-bold text-gray-800">{t.appTitle}</span>
            <span>—</span>
            <span>{t.empoweringCitizens}</span>
          </div>

          <div className="flex items-center gap-4">
            <a
              href="https://nalsa.gov.in"
              target="_blank"
              rel="noreferrer"
              className="text-primary-700 hover:text-primary-900 inline-flex items-center gap-1 font-medium"
            >
              {t.nalsaPortal} <ExternalLink className="w-3 h-3" />
            </a>
            <span>•</span>
            <span>{t.tollFreeHelpline}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

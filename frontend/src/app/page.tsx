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
} from 'lucide-react';
import LanguageSelector from '@/components/LanguageSelector';
import ProfileSelector from '@/components/ProfileSelector';
import ChatInterface from '@/components/ChatInterface';
import DocumentUpload from '@/components/DocumentUpload';
import { UserProfileType, checkHealth, UploadResponse } from '@/lib/api';
import { getUITranslations } from '@/lib/i18n';

export default function Home() {
  const [selectedLanguage, setSelectedLanguage] = useState('hi');
  const [selectedProfile, setSelectedProfile] = useState<UserProfileType>('general');
  const [activeTab, setActiveTab] = useState<'chat' | 'upload' | 'reference'>('chat');
  const [backendStatus, setBackendStatus] = useState<'checking' | 'healthy' | 'offline'>('checking');
  const [uploadedFiles, setUploadedFiles] = useState<UploadResponse[]>([]);

  const t = getUITranslations(selectedLanguage);

  useEffect(() => {
    checkHealth()
      .then((res) => {
        if (res.status === 'healthy') setBackendStatus('healthy');
        else setBackendStatus('offline');
      })
      .catch(() => setBackendStatus('offline'));
  }, []);

  const handleDocumentUploaded = (res: UploadResponse) => {
    setUploadedFiles((prev) => [res, ...prev]);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-gray-900 flex flex-col font-sans">
      {/* Top Banner / Emergency Legal Aid Bar */}
      <div className="bg-primary-950 text-white text-xs px-4 py-2 border-b border-primary-900">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="bg-accent-500 text-white font-bold text-[10px] px-2 py-0.5 rounded uppercase">
              {t.emergencyTitle}
            </span>
            <span className="font-medium text-gray-200">
              {t.legalAidText}
            </span>
            <a
              href="tel:15100"
              className="font-bold text-accent-300 hover:text-accent-200 underline inline-flex items-center gap-1"
            >
              <PhoneCall className="w-3 h-3" /> {t.tollFree}
            </a>
          </div>

          <div className="flex items-center gap-4 text-gray-300 text-[11px]">
            <span>{t.police}</span>
            <span>{t.cyberCrime}</span>
            <span>{t.women}</span>
          </div>
        </div>
      </div>

      {/* Main Header */}
      <header className="bg-white border-b border-gray-200 shadow-2xs sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-primary-700 to-primary-900 flex items-center justify-center text-white shadow-md">
              <Scale className="w-6 h-6 text-accent-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-extrabold text-primary-900 tracking-tight">
                  {t.appTitle}
                </h1>
                <span className="text-xs font-semibold text-gray-400">|</span>
                <span className="text-base font-bold text-gray-800">
                  Nyayavarta
                </span>
                <span className="hidden sm:inline-flex items-center gap-1 bg-green-50 text-green-700 text-[10px] font-semibold px-2 py-0.5 rounded-full border border-green-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  {backendStatus === 'healthy' ? t.apiOnline : 'Active'}
                </span>
              </div>
              <p className="text-xs text-gray-500">
                {t.appSubtitle}
              </p>
            </div>
          </div>

          {/* Controls: Language Selector */}
          <div className="flex items-center gap-3">
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
        <div className="flex items-center justify-between border-b border-gray-200">
          <nav className="flex space-x-2 sm:space-x-4">
            <button
              type="button"
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2 py-3 px-4 font-semibold text-sm border-b-2 transition-all ${
                activeTab === 'chat'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              {t.tabChat}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('upload')}
              className={`flex items-center gap-2 py-3 px-4 font-semibold text-sm border-b-2 transition-all ${
                activeTab === 'upload'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Upload className="w-4 h-4" />
              {t.tabUpload}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('reference')}
              className={`flex items-center gap-2 py-3 px-4 font-semibold text-sm border-b-2 transition-all ${
                activeTab === 'reference'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              {t.tabMatrix}
            </button>
          </nav>

          <div className="hidden md:flex items-center gap-2 text-xs text-gray-500">
            <ShieldCheck className="w-4 h-4 text-primary-600" />
            <span>{t.ragTag}</span>
          </div>
        </div>

        {/* Tab 1: Chat Interface */}
        {activeTab === 'chat' && (
          <div className="space-y-5">
            {/* Persona Selector Banner */}
            <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-200">
              <ProfileSelector
                selectedProfile={selectedProfile}
                onProfileChange={setSelectedProfile}
                selectedLanguage={selectedLanguage}
              />
            </div>

            {/* Chat Area */}
            <ChatInterface
              selectedLanguage={selectedLanguage}
              selectedProfile={selectedProfile}
            />
          </div>
        )}

        {/* Tab 2: Document Upload & Knowledge Base */}
        {activeTab === 'upload' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <DocumentUpload onUploadSuccess={handleDocumentUploaded} />

              {/* Uploaded Documents History */}
              <div className="card">
                <h4 className="font-bold text-gray-800 text-sm mb-3">
                  Dynamically Ingested Files (अपलोड किए गए दस्तावेज़)
                </h4>
                {uploadedFiles.length === 0 ? (
                  <p className="text-xs text-gray-400 italic">
                    No custom documents uploaded in this session yet. Uploaded PDF or Word files will be indexed into FAISS vector space and BM25 corpus instantly.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {uploadedFiles.map((file, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-200 text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-green-600" />
                          <span className="font-semibold text-gray-800">{file.filename}</span>
                        </div>
                        <span className="bg-primary-100 text-primary-800 px-2 py-0.5 rounded-full text-[11px] font-medium">
                          {file.chunks_created} chunks indexed
                        </span>
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
                  GraphRAG Architecture (Neo4j)
                </h4>
                <p className="text-xs text-gray-300 leading-relaxed mb-4">
                  Nyayavarta combines Neo4j Knowledge Graph traversal with BM25 keyword search to maximize legal accuracy.
                </p>
                <div className="space-y-2.5 text-xs">
                  <div className="flex justify-between pb-1.5 border-b border-white/10">
                    <span className="text-gray-300">Knowledge Graph</span>
                    <span className="font-mono font-semibold text-white">Neo4j (Cypher Traversal)</span>
                  </div>
                  <div className="flex justify-between pb-1.5 border-b border-white/10">
                    <span className="text-gray-300">Keyword Retrieval</span>
                    <span className="font-mono font-semibold text-white">rank-bm25 (BM25Okapi)</span>
                  </div>
                  <div className="flex justify-between pb-1.5 border-b border-white/10">
                    <span className="text-gray-300">Orchestration</span>
                    <span className="font-mono font-semibold text-accent-300">LangChain Neo4jGraph</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Statutory Graph Data</span>
                    <span className="font-mono font-semibold text-white">IPC/CrPC → BNS/BNSS/BSA</span>
                  </div>
                </div>
              </div>

              <div className="card">
                <h4 className="font-bold text-gray-800 text-sm mb-2">
                  Document Guidelines
                </h4>
                <ul className="text-xs text-gray-600 space-y-2 list-disc list-inside">
                  <li>Supported: FIR copies, court petitions, bail orders, legal contracts.</li>
                  <li>Text extraction via <strong>PyMuPDF</strong> with page-level metadata.</li>
                  <li>Max file size: 20MB.</li>
                  <li>Indexed chunks are automatically retrieved in subsequent chat queries.</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Law Transition Matrix */}
        {activeTab === 'reference' && (
          <div className="card space-y-4">
            <div>
              <h3 className="text-base font-bold text-gray-900">
                {t.matrixTitle}
              </h3>
              <p className="text-xs text-gray-500 mt-1">
                {t.matrixSubtitle}
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-primary-50 text-primary-950 border-b border-primary-200">
                    <th className="p-3 font-bold">{t.matrixHeaders.crime}</th>
                    <th className="p-3 font-bold">{t.matrixHeaders.oldLaw}</th>
                    <th className="p-3 font-bold">{t.matrixHeaders.newLaw}</th>
                    <th className="p-3 font-bold">{t.matrixHeaders.note}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  <tr className="hover:bg-gray-50">
                    <td className="p-3 font-semibold text-gray-900">Murder</td>
                    <td className="p-3 font-mono text-gray-600">IPC Section 302</td>
                    <td className="p-3 font-mono font-bold text-primary-700">BNS Section 103</td>
                    <td className="p-3 text-gray-600">Punishment remains death or life imprisonment, and fine.</td>
                  </tr>
                  <tr className="hover:bg-gray-50">
                    <td className="p-3 font-semibold text-gray-900">Cheating & Fraud</td>
                    <td className="p-3 font-mono text-gray-600">IPC Section 420</td>
                    <td className="p-3 font-mono font-bold text-primary-700">BNS Section 318</td>
                    <td className="p-3 text-gray-600">Dishonest inducement of property covered under Section 318.</td>
                  </tr>
                  <tr className="hover:bg-gray-50">
                    <td className="p-3 font-semibold text-gray-900">First Information Report (FIR)</td>
                    <td className="p-3 font-mono text-gray-600">CrPC Section 154</td>
                    <td className="p-3 font-mono font-bold text-primary-700">BNSS Section 173</td>
                    <td className="p-3 text-gray-600">Formalizes Zero FIR and electronic FIR (e-FIR).</td>
                  </tr>
                  <tr className="hover:bg-gray-50">
                    <td className="p-3 font-semibold text-gray-900">Cruelty by Husband / Relatives</td>
                    <td className="p-3 font-mono text-gray-600">IPC Section 498A</td>
                    <td className="p-3 font-mono font-bold text-primary-700">BNS Section 86</td>
                    <td className="p-3 text-gray-600">Substantive provisions maintained with enhanced focus on women safety.</td>
                  </tr>
                  <tr className="hover:bg-gray-50">
                    <td className="p-3 font-semibold text-gray-900">Electronic Evidence</td>
                    <td className="p-3 font-mono text-gray-600">Evidence Act 65B</td>
                    <td className="p-3 font-mono font-bold text-primary-700">BSA Section 63</td>
                    <td className="p-3 text-gray-600">Expanded scope to server logs, GPS, emails, and mobile data.</td>
                  </tr>
                  <tr className="hover:bg-gray-50">
                    <td className="p-3 font-semibold text-gray-900">Theft</td>
                    <td className="p-3 font-mono text-gray-600">IPC Section 379</td>
                    <td className="p-3 font-mono font-bold text-primary-700">BNS Section 305</td>
                    <td className="p-3 text-gray-600">Community service added as punishment for petty theft.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-gray-500">
          <div className="flex items-center gap-2">
            <span className="font-bold text-gray-800">न्यायवार्ता (Nyayavarta)</span>
            <span>—</span>
            <span>Empowering Indian Citizens with AI Legal Literacy</span>
          </div>

          <div className="flex items-center gap-4">
            <a
              href="https://nalsa.gov.in"
              target="_blank"
              rel="noreferrer"
              className="text-primary-700 hover:text-primary-900 inline-flex items-center gap-1 font-medium"
            >
              NALSA Official Portal <ExternalLink className="w-3 h-3" />
            </a>
            <span>•</span>
            <span>Toll-Free Helpline: <strong>15100</strong></span>
          </div>
        </div>
      </footer>
    </div>
  );
}

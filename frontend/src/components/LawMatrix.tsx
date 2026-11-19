'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  BookOpen,
  Scale,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  FileText,
  Gavel,
  CheckCircle,
  ExternalLink,
  Filter,
  X,
  Copy,
  Check,
  Info,
  ShieldCheck,
  AlertCircle,
  Clock,
  HelpCircle,
} from 'lucide-react';
import { fetchLawMatrix, LawTransition, CasePrecedent } from '@/lib/api';

interface LawMatrixProps {
  onSelectQuery?: (query: string) => void;
  className?: string;
}

type MatrixTab = 'statutes' | 'precedents';
type CategoryFilter = 'all' | 'bns' | 'bnss' | 'bsa' | 'special';

export default function LawMatrix({ onSelectQuery, className = '' }: LawMatrixProps) {
  const [activeSubTab, setActiveSubTab] = useState<MatrixTab>('statutes');
  const [selectedCategory, setSelectedCategory] = useState<CategoryFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [transitions, setTransitions] = useState<LawTransition[]>([]);
  const [precedents, setPrecedents] = useState<CasePrecedent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Detail Modal States
  const [selectedTransition, setSelectedTransition] = useState<LawTransition | null>(null);
  const [selectedPrecedent, setSelectedPrecedent] = useState<CasePrecedent | null>(null);
  const [isCopied, setIsCopied] = useState(false);

  useEffect(() => {
    loadMatrixData();
  }, []);

  const loadMatrixData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchLawMatrix();
      setTransitions(data.transitions || []);
      setPrecedents(data.precedents || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch matrix data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  // Close modals on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSelectedTransition(null);
        setSelectedPrecedent(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Filtered transitions based on Category and Search
  const filteredTransitions = useMemo(() => {
    return transitions.filter((t) => {
      const matchesCat =
        selectedCategory === 'all' || t.category === selectedCategory;

      if (!matchesCat) return false;

      if (!searchQuery.trim()) return true;

      const q = searchQuery.toLowerCase().trim();
      return (
        t.subject.toLowerCase().includes(q) ||
        t.old_law.toLowerCase().includes(q) ||
        t.new_law.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q) ||
        t.key_changes.toLowerCase().includes(q) ||
        (t.punishment_comparison && t.punishment_comparison.toLowerCase().includes(q))
      );
    });
  }, [transitions, selectedCategory, searchQuery]);

  // Filtered precedents based on Search
  const filteredPrecedents = useMemo(() => {
    if (!searchQuery.trim()) return precedents;
    const q = searchQuery.toLowerCase().trim();
    return precedents.filter(
      (p) =>
        p.title.toLowerCase().includes(q) ||
        p.citation.toLowerCase().includes(q) ||
        p.headnote.toLowerCase().includes(q) ||
        p.ratio_decidendi.toLowerCase().includes(q) ||
        (p.significance && p.significance.toLowerCase().includes(q)) ||
        (p.practical_impact && p.practical_impact.toLowerCase().includes(q)) ||
        p.applied_sections.some((s) => s.toLowerCase().includes(q))
    );
  }, [precedents, searchQuery]);

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-primary-950 via-primary-900 to-slate-900 border border-primary-800 text-white rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5 max-w-2xl">
            <div className="inline-flex items-center gap-1.5 bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2.5 py-0.5 rounded-full text-xs font-semibold">
              <Scale className="w-3.5 h-3.5" />
              Official Indian Criminal Law Concordance & Precedent Corpus
            </div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Indian Law Transition Matrix & Landmark Precedents
            </h2>
            <p className="text-xs text-slate-300 leading-relaxed">
              Explore <strong>{transitions.length} statutory transitions</strong> (IPC ↔ BNS, CrPC ↔ BNSS, Evidence Act ↔ BSA, Special Acts) and <strong>{precedents.length} Landmark Supreme Court Precedents</strong>. Click on any provision or case to view complete comparative penalties, procedural classifications, and citizen rights.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="bg-white/10 backdrop-blur-xs border border-white/15 rounded-xl p-3 text-center min-w-[100px]">
              <span className="block text-2xl font-black text-amber-300">{transitions.length}</span>
              <span className="text-[10px] text-slate-300 uppercase tracking-wider font-semibold">Transitions</span>
            </div>
            <div className="bg-white/10 backdrop-blur-xs border border-white/15 rounded-xl p-3 text-center min-w-[100px]">
              <span className="block text-2xl font-black text-emerald-300">{precedents.length}</span>
              <span className="text-[10px] text-slate-300 uppercase tracking-wider font-semibold">SC Precedents</span>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Sub-Tabs: Statutes vs Precedents */}
        <div className="flex items-center p-1 bg-slate-200/80 rounded-xl max-w-fit shadow-2xs">
          <button
            type="button"
            onClick={() => setActiveSubTab('statutes')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeSubTab === 'statutes'
                ? 'bg-white text-primary-950 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Statutory Concordance ({transitions.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveSubTab('precedents')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeSubTab === 'precedents'
                ? 'bg-white text-primary-950 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Gavel className="w-3.5 h-3.5" />
            <span>Landmark Precedents ({precedents.length})</span>
          </button>
        </div>

        {/* Live Search */}
        <div className="relative flex-1 sm:max-w-md">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={
              activeSubTab === 'statutes'
                ? 'Search offense, section (e.g. 420, 302, 173), or penalty...'
                : 'Search precedent (e.g. Lalita Kumari, Arnesh Kumar, Bail)...'
            }
            className="w-full pl-9 pr-8 py-2 text-xs bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 text-slate-900 placeholder:text-slate-400 shadow-2xs"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs px-1"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Category Pills (Only for Statutes view) */}
      {activeSubTab === 'statutes' && (
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
          <span className="text-slate-400 text-[11px] font-semibold mr-1 flex items-center gap-1">
            <Filter className="w-3 h-3" /> Category:
          </span>
          {[
            { id: 'all', label: `All (${transitions.length})` },
            { id: 'bns', label: 'BNS (Penal)' },
            { id: 'bnss', label: 'BNSS (Procedure & Police)' },
            { id: 'bsa', label: 'BSA (Evidence & Records)' },
            { id: 'special', label: 'Special & Central Acts' },
          ].map((cat) => (
            <button
              key={cat.id}
              type="button"
              onClick={() => setSelectedCategory(cat.id as CategoryFilter)}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all cursor-pointer whitespace-nowrap text-xs ${
                selectedCategory === cat.id
                  ? 'bg-primary-900 text-white shadow-2xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      )}

      {/* Main Content Area */}
      {isLoading ? (
        <div className="card p-12 text-center text-slate-500 space-y-2">
          <Scale className="w-8 h-8 mx-auto text-primary-600 animate-pulse" />
          <p className="text-xs font-semibold">Loading statutory concordance matrix & precedents...</p>
        </div>
      ) : error ? (
        <div className="card p-6 bg-red-50 border-red-200 text-red-800 text-xs">
          Failed to load matrix data: {error}
        </div>
      ) : activeSubTab === 'statutes' ? (
        /* ============================================================ */
        /* STATUTORY TRANSITIONS TABLE                                  */
        /* ============================================================ */
        <div className="space-y-3">
          <div className="overflow-x-auto rounded-2xl border border-slate-200 shadow-2xs bg-white">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-900 border-b border-slate-200">
                  <th className="p-3.5 font-bold w-1/5">Subject / Offense</th>
                  <th className="p-3.5 font-bold w-1/5">Colonial / Old Law</th>
                  <th className="p-3.5 font-bold w-1/5">Modern Law (2023 / Special)</th>
                  <th className="p-3.5 font-bold w-1/4">Key Statutory Transition & Penalty</th>
                  <th className="p-3.5 font-bold text-center w-32">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredTransitions.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-slate-400 italic">
                      No statutory provisions matched your search "{searchQuery}".
                    </td>
                  </tr>
                ) : (
                  filteredTransitions.map((t) => (
                    <tr
                      key={t.id}
                      onClick={() => setSelectedTransition(t)}
                      className="hover:bg-primary-50/40 transition-colors cursor-pointer group"
                    >
                      <td className="p-3.5 align-top">
                        <div className="font-bold text-slate-900 leading-snug group-hover:text-primary-800 transition-colors">
                          {t.subject}
                        </div>
                        <span className="inline-block mt-1 text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                          {t.category_label}
                        </span>
                      </td>

                      <td className="p-3.5 align-top">
                        <div className="font-mono text-xs font-semibold text-rose-700 bg-rose-50 px-2 py-1 rounded-md border border-rose-100 inline-block mb-1">
                          {t.old_law}
                        </div>
                      </td>

                      <td className="p-3.5 align-top">
                        <div className="font-mono text-xs font-bold text-emerald-800 bg-emerald-50 px-2 py-1 rounded-md border border-emerald-200 inline-block mb-1">
                          {t.new_law}
                        </div>
                      </td>

                      <td className="p-3.5 align-top text-slate-700 leading-relaxed text-[11px]">
                        <p className="font-medium text-slate-800 mb-1">{t.key_changes}</p>
                        <p className="text-slate-500 text-[10px] line-clamp-2">{t.description}</p>
                      </td>

                      <td className="p-3.5 align-top text-center" onClick={(e) => e.stopPropagation()}>
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => setSelectedTransition(t)}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-semibold transition-all cursor-pointer whitespace-nowrap"
                            title="View full details and penalties"
                          >
                            <Info className="w-3 h-3 text-primary-600" />
                            <span>Details</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => onSelectQuery?.(t.suggested_query)}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-primary-50 hover:bg-primary-600 text-primary-800 hover:text-white border border-primary-200 text-[11px] font-semibold transition-all cursor-pointer shadow-2xs whitespace-nowrap"
                            title="Ask Nyayavarta AI in chat"
                          >
                            <Sparkles className="w-3 h-3" />
                            <span>Ask AI</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500 px-1">
            <span>Showing {filteredTransitions.length} of {transitions.length} statutory transitions • Click any row for complete details</span>
            <span>All transitions indexed in Neo4j Knowledge Graph</span>
          </div>
        </div>
      ) : (
        /* ============================================================ */
        /* LANDMARK PRECEDENTS CARDS                                    */
        /* ============================================================ */
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredPrecedents.length === 0 ? (
              <div className="col-span-2 card p-8 text-center text-slate-400 italic">
                No landmark case precedents matched your search "{searchQuery}".
              </div>
            ) : (
              filteredPrecedents.map((p, idx) => (
                <div
                  key={idx}
                  onClick={() => setSelectedPrecedent(p)}
                  className="card hover:border-primary-400 hover:shadow-md transition-all flex flex-col justify-between space-y-3 bg-white cursor-pointer group"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="font-bold text-slate-900 text-sm leading-snug group-hover:text-primary-800 transition-colors">
                          {p.title}
                        </h4>
                        <div className="flex items-center gap-2 mt-1 text-[11px] font-mono text-slate-500">
                          <span className="font-semibold text-primary-700 bg-primary-50 px-1.5 py-0.5 rounded border border-primary-100">
                            {p.citation}
                          </span>
                          {p.neutral_citation && <span>• {p.neutral_citation}</span>}
                          <span>• {p.year}</span>
                        </div>
                      </div>

                      <span className="flex-shrink-0 bg-amber-50 text-amber-900 border border-amber-200 px-2 py-0.5 rounded text-[10px] font-semibold uppercase">
                        SC Landmark
                      </span>
                    </div>

                    <div className="space-y-1.5 text-xs text-slate-700">
                      <p className="font-medium text-slate-900 bg-slate-50 p-2.5 rounded-lg border border-slate-100 text-[11px] leading-relaxed">
                        <strong>Headnote:</strong> {p.headnote}
                      </p>
                      <p className="text-slate-600 text-[11px] leading-relaxed line-clamp-3">
                        <strong>Ratio Decidendi:</strong> {p.ratio_decidendi}
                      </p>
                    </div>

                    {/* Applied Sections */}
                    <div className="flex flex-wrap gap-1 pt-1">
                      {p.applied_sections.map((sec, sIdx) => (
                        <span
                          key={sIdx}
                          className="bg-slate-100 text-slate-700 font-mono text-[10px] px-1.5 py-0.5 rounded border border-slate-200"
                        >
                          {sec.replace('_', ' ')}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Card Action Footer */}
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      onClick={() => setSelectedPrecedent(p)}
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary-700 hover:text-primary-900 cursor-pointer"
                    >
                      <Info className="w-3.5 h-3.5" />
                      <span>View Full Ruling & Impact</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => onSelectQuery?.(p.suggested_query)}
                      className="inline-flex items-center gap-1.5 bg-primary-50 hover:bg-primary-600 text-primary-800 hover:text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer shadow-2xs"
                    >
                      <Sparkles className="w-3 h-3" />
                      <span>Ask AI</span>
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="text-xs text-slate-500 text-right px-1">
            Showing {filteredPrecedents.length} landmark Supreme Court judgments indexed in GraphRAG • Click any case for full details
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* STATUTORY TRANSITION FULL DETAIL MODAL                       */}
      {/* ============================================================ */}
      {selectedTransition && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 overflow-y-auto animate-fade-in">
          <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="p-4 sm:p-5 bg-gradient-to-r from-slate-900 via-primary-950 to-slate-900 text-white flex items-start justify-between gap-3 border-b border-slate-800">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    {selectedTransition.category_label}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">ID: {selectedTransition.id}</span>
                </div>
                <h3 className="text-lg font-bold text-white leading-tight">
                  {selectedTransition.subject}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedTransition(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors cursor-pointer"
                title="Close (Esc)"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 overflow-y-auto space-y-4 text-xs leading-relaxed text-slate-800">
              {/* Old vs New Law Box */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <div className="space-y-1">
                  <span className="text-[11px] font-semibold text-rose-700 uppercase tracking-wider block">
                    Colonial / Former Law
                  </span>
                  <div className="font-mono text-xs font-bold text-rose-900 bg-rose-50/80 p-2 rounded-lg border border-rose-200">
                    {selectedTransition.old_law}
                  </div>
                </div>
                <div className="space-y-1">
                  <span className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider block">
                    Modern Law (2023 / Present)
                  </span>
                  <div className="font-mono text-xs font-bold text-emerald-950 bg-emerald-50 p-2 rounded-lg border border-emerald-200">
                    {selectedTransition.new_law}
                  </div>
                </div>
              </div>

              {/* Key Statutory Transition */}
              <div className="space-y-1.5">
                <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                  <Scale className="w-4 h-4 text-primary-600" /> Key Statutory Shift & Transition
                </h4>
                <p className="bg-primary-50/60 p-3 rounded-xl border border-primary-100 text-primary-950 font-medium">
                  {selectedTransition.key_changes}
                </p>
              </div>

              {/* Punishment & Severity Comparison */}
              {selectedTransition.punishment_comparison && (
                <div className="space-y-1.5">
                  <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                    <ShieldAlert className="w-4 h-4 text-amber-600" /> Punishment & Severity Comparison
                  </h4>
                  <div className="bg-amber-50/70 p-3 rounded-xl border border-amber-200 text-amber-950 whitespace-pre-line font-mono text-[11px]">
                    {selectedTransition.punishment_comparison}
                  </div>
                </div>
              )}

              {/* Procedural Classification */}
              {selectedTransition.procedural_classification && (
                <div className="space-y-1.5">
                  <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                    <Gavel className="w-4 h-4 text-indigo-600" /> Procedural & Court Classification
                  </h4>
                  <div className="p-2.5 rounded-xl bg-indigo-50/60 border border-indigo-100 text-indigo-950 font-semibold text-[11px]">
                    {selectedTransition.procedural_classification}
                  </div>
                </div>
              )}

              {/* Practical Guidance for Citizens */}
              {selectedTransition.practical_citizen_advice && (
                <div className="space-y-1.5">
                  <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" /> Practical Guidance & Citizen Rights
                  </h4>
                  <div className="p-3 rounded-xl bg-emerald-50/60 border border-emerald-200 text-emerald-950">
                    {selectedTransition.practical_citizen_advice}
                  </div>
                </div>
              )}

              {/* Full Description & Scope */}
              <div className="space-y-1.5">
                <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                  <FileText className="w-4 h-4 text-slate-600" /> Detailed Legal Description & Ingredients
                </h4>
                <p className="text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200 text-[11px] leading-relaxed">
                  {selectedTransition.description}
                </p>
              </div>

              {/* Full Statutory Text (if present) */}
              {selectedTransition.full_statutory_text && (
                <div className="space-y-1.5">
                  <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                    <BookOpen className="w-4 h-4 text-slate-600" /> Statutory Text Extract
                  </h4>
                  <div className="bg-slate-900 text-slate-100 p-3 rounded-xl text-[11px] font-mono whitespace-pre-line leading-relaxed">
                    {selectedTransition.full_statutory_text}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2">
              <button
                type="button"
                onClick={() =>
                  handleCopyText(
                    `${selectedTransition.subject}\nFormer: ${selectedTransition.old_law}\nModern: ${selectedTransition.new_law}\nKey Changes: ${selectedTransition.key_changes}\n${selectedTransition.punishment_comparison || ''}`
                  )
                }
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-white border border-slate-300 px-3 py-2 rounded-xl transition-colors cursor-pointer"
              >
                {isCopied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{isCopied ? 'Copied' : 'Copy Details'}</span>
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedTransition(null)}
                  className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 rounded-xl hover:bg-slate-200/60 transition-colors cursor-pointer"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const q = selectedTransition.suggested_query;
                    setSelectedTransition(null);
                    onSelectQuery?.(q);
                  }}
                  className="inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white text-xs font-bold px-4 py-2 rounded-xl shadow-xs transition-all cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                  <span>Ask AI in Legal Chat</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* LANDMARK PRECEDENT FULL DETAIL MODAL                         */}
      {/* ============================================================ */}
      {selectedPrecedent && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 overflow-y-auto animate-fade-in">
          <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="p-4 sm:p-5 bg-gradient-to-r from-slate-900 via-primary-950 to-slate-900 text-white flex items-start justify-between gap-3 border-b border-slate-800">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    Supreme Court of India
                  </span>
                  <span className="text-xs text-slate-400 font-mono">Year {selectedPrecedent.year}</span>
                </div>
                <h3 className="text-lg font-bold text-white leading-tight">
                  {selectedPrecedent.title}
                </h3>
                <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
                  <span className="text-amber-300 font-semibold">{selectedPrecedent.citation}</span>
                  {selectedPrecedent.neutral_citation && <span>• {selectedPrecedent.neutral_citation}</span>}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedPrecedent(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors cursor-pointer"
                title="Close (Esc)"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 overflow-y-auto space-y-4 text-xs leading-relaxed text-slate-800">
              {/* Bench Information */}
              {selectedPrecedent.bench && (
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-700 flex items-center gap-2">
                  <Gavel className="w-4 h-4 text-slate-500 flex-shrink-0" />
                  <span><strong>Bench:</strong> {selectedPrecedent.bench}</span>
                </div>
              )}

              {/* Headnote */}
              <div className="space-y-1.5">
                <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                  <BookOpen className="w-4 h-4 text-primary-600" /> Case Subject & Headnote
                </h4>
                <div className="bg-primary-50/70 p-3 rounded-xl border border-primary-200 text-primary-950 font-medium">
                  {selectedPrecedent.headnote}
                </div>
              </div>

              {/* Ratio Decidendi (Core Binding Law) */}
              <div className="space-y-1.5">
                <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                  <Scale className="w-4 h-4 text-indigo-600" /> Ratio Decidendi (Binding Principle of Law)
                </h4>
                <div className="bg-indigo-50/60 p-3.5 rounded-xl border border-indigo-200 text-indigo-950 leading-relaxed font-sans text-xs">
                  {selectedPrecedent.ratio_decidendi}
                </div>
              </div>

              {/* Constitutional Significance */}
              {selectedPrecedent.significance && (
                <div className="space-y-1.5">
                  <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" /> Constitutional & Historical Significance
                  </h4>
                  <div className="bg-emerald-50/70 p-3 rounded-xl border border-emerald-200 text-emerald-950">
                    {selectedPrecedent.significance}
                  </div>
                </div>
              )}

              {/* Practical Citizen Impact */}
              {selectedPrecedent.practical_impact && (
                <div className="space-y-1.5">
                  <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                    <AlertCircle className="w-4 h-4 text-amber-600" /> Everyday Practical Impact for Citizens
                  </h4>
                  <div className="bg-amber-50/70 p-3 rounded-xl border border-amber-200 text-amber-950">
                    {selectedPrecedent.practical_impact}
                  </div>
                </div>
              )}

              {/* Applied Sections */}
              <div className="space-y-1.5">
                <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                  <FileText className="w-4 h-4 text-slate-600" /> Applied Statutory Sections
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {selectedPrecedent.applied_sections.map((sec, sIdx) => (
                    <span
                      key={sIdx}
                      className="bg-slate-100 text-slate-800 font-mono text-xs px-2 py-1 rounded-md border border-slate-200 font-semibold"
                    >
                      {sec.replace('_', ' ')}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2">
              <button
                type="button"
                onClick={() =>
                  handleCopyText(
                    `${selectedPrecedent.title} (${selectedPrecedent.citation})\nRatio Decidendi: ${selectedPrecedent.ratio_decidendi}\nHeadnote: ${selectedPrecedent.headnote}`
                  )
                }
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-white border border-slate-300 px-3 py-2 rounded-xl transition-colors cursor-pointer"
              >
                {isCopied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{isCopied ? 'Copied' : 'Copy Citation'}</span>
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedPrecedent(null)}
                  className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 rounded-xl hover:bg-slate-200/60 transition-colors cursor-pointer"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const q = selectedPrecedent.suggested_query;
                    setSelectedPrecedent(null);
                    onSelectQuery?.(q);
                  }}
                  className="inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white text-xs font-bold px-4 py-2 rounded-xl shadow-xs transition-all cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                  <span>Ask AI About This Case</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

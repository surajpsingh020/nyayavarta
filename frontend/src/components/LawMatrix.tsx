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
        t.key_changes.toLowerCase().includes(q)
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
              Official 2024 Criminal Law Transition Reference
            </div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Indian Law Transition Matrix & Landmark Precedents
            </h2>
            <p className="text-xs text-primary-200 leading-relaxed">
              Explore how colonial statutes (IPC, CrPC, Indian Evidence Act) map to modernized laws (BNS, BNSS, BSA, 2023) alongside Special Central Acts and landmark Supreme Court rulings.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="bg-white/10 text-white text-xs px-3 py-1.5 rounded-xl border border-white/10 font-mono">
              26+ Central Acts
            </span>
            <span className="bg-amber-400/20 text-amber-300 text-xs px-3 py-1.5 rounded-xl border border-amber-400/30 font-mono">
              12 SC Precedents
            </span>
          </div>
        </div>
      </div>

      {/* Navigation Sub-Tabs & Live Search */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Sub-tab selection */}
        <div className="inline-flex bg-slate-100 p-1 rounded-xl border border-slate-200 shadow-2xs">
          <button
            type="button"
            onClick={() => setActiveSubTab('statutes')}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              activeSubTab === 'statutes'
                ? 'bg-white text-primary-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            Statutory Transitions ({transitions.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveSubTab('precedents')}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              activeSubTab === 'precedents'
                ? 'bg-white text-primary-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Gavel className="w-3.5 h-3.5" />
            Landmark Precedents ({precedents.length})
          </button>
        </div>

        {/* Search Bar */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={
              activeSubTab === 'statutes'
                ? 'Search crime, section (e.g. 420, 302, 173), or act...'
                : 'Search case name (e.g. Lalita Kumari, Arnesh Kumar)...'
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
            { id: 'bnss', label: 'BNSS (Procedure & FIR)' },
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
          <p className="text-xs font-semibold">Loading statutory concordance matrix...</p>
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
                  <th className="p-3.5 font-bold w-1/5">Subject / Offence</th>
                  <th className="p-3.5 font-bold w-1/5">Colonial / Old Law</th>
                  <th className="p-3.5 font-bold w-1/5">Modern Law (2023 / Special)</th>
                  <th className="p-3.5 font-bold w-1/4">Key Statutory Transition</th>
                  <th className="p-3.5 font-bold text-center w-28">Action</th>
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
                    <tr key={t.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="p-3.5 align-top">
                        <div className="font-bold text-slate-900 leading-snug">{t.subject}</div>
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

                      <td className="p-3.5 align-top text-center">
                        <button
                          type="button"
                          onClick={() => onSelectQuery?.(t.suggested_query)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-primary-50 hover:bg-primary-600 text-primary-800 hover:text-white border border-primary-200 text-xs font-semibold transition-all cursor-pointer shadow-2xs whitespace-nowrap"
                          title="Ask Nyayavarta AI about this legal section in chat"
                        >
                          <Sparkles className="w-3 h-3" />
                          <span>Ask AI</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between text-xs text-slate-500 px-1">
            <span>Showing {filteredTransitions.length} of {transitions.length} statutory transitions</span>
            <span>All transitions cross-referenced in Neo4j Knowledge Graph</span>
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
                  className="card hover:border-primary-400 hover:shadow-sm transition-all flex flex-col justify-between space-y-3 bg-white"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="font-bold text-slate-900 text-sm leading-snug">
                          {p.title}
                        </h4>
                        <div className="flex items-center gap-2 mt-1 text-[11px] font-mono text-slate-500">
                          <span className="font-semibold text-primary-700 bg-primary-50 px-1.5 py-0.5 rounded border border-primary-100">
                            {p.citation}
                          </span>
                          {p.neutral_citation && (
                            <span>{p.neutral_citation}</span>
                          )}
                          <span>• {p.year}</span>
                        </div>
                      </div>

                      <span className="flex-shrink-0 bg-amber-50 text-amber-900 border border-amber-200 px-2 py-0.5 rounded text-[10px] font-semibold uppercase">
                        SC Landmark
                      </span>
                    </div>

                    <div className="space-y-1.5 text-xs text-slate-700">
                      <p className="font-medium text-slate-900 bg-slate-50 p-2 rounded-lg border border-slate-100 text-[11px]">
                        <strong>Headnote:</strong> {p.headnote}
                      </p>
                      <p className="text-slate-600 text-[11px] leading-relaxed">
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

                  {/* Ask AI Action */}
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                    <span className="text-[10px] text-slate-400 italic">
                      {p.bench ? `Bench: ${p.bench.split(',')[0]} et al.` : 'Supreme Court of India'}
                    </span>
                    <button
                      type="button"
                      onClick={() => onSelectQuery?.(p.suggested_query)}
                      className="inline-flex items-center gap-1.5 bg-primary-50 hover:bg-primary-600 text-primary-800 hover:text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer shadow-2xs"
                    >
                      <Sparkles className="w-3 h-3" />
                      <span>Ask AI About This Case</span>
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="text-xs text-slate-500 text-right px-1">
            Showing {filteredPrecedents.length} landmark Supreme Court judgments indexed in GraphRAG
          </div>
        </div>
      )}
    </div>
  );
}

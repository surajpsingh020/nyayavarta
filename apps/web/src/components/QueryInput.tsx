import React, { useState } from 'react';
import { RAGQueryRequest } from '../types/rag';
import { Search, Loader2, SlidersHorizontal, Sparkles } from 'lucide-react';

interface QueryInputProps {
  onSubmit: (params: RAGQueryRequest) => void;
  isLoading: boolean;
}

export const CANONICAL_PRESETS = [
  {
    id: 'DEMO_Q1',
    label: '1. Supported Rule',
    tag: 'verified_supported',
    category: 'Corpus Grounded',
    query: 'Can the rules of selection or eligibility criteria be changed after the recruitment process has commenced under Rajasthan High Court rules?',
    provider: 'mock' as const,
  },
  {
    id: 'DEMO_Q2',
    label: '2. Missing Proviso',
    tag: 'qualified_answer',
    category: 'Partially Supported',
    query: 'Can the authorized officer unilaterally extend the 15-day period for deposit of 75% purchase money under SARFAESI Rule 9(4) without consent of the borrower?',
    provider: 'mock_partial' as const,
  },
  {
    id: 'DEMO_Q3',
    label: '3. Statutory Prohibition',
    tag: 'insufficient_evidence',
    category: 'Direct Contradiction',
    query: 'Are seeds, plant varieties, and essentially biological processes patentable under Section 3(j) of the Indian Patents Act, 1970?',
    provider: 'mock' as const,
  },
  {
    id: 'DEMO_Q4',
    label: '4. Out of Corpus',
    tag: 'insufficient_evidence',
    category: 'Clean Abstention',
    query: 'What is the period of limitation for filing an in rem admiralty action against an arrested foreign cargo vessel under the Admiralty Act, 2017?',
    provider: 'mock' as const,
  },
];

export const QueryInput: React.FC<QueryInputProps> = ({ onSubmit, isLoading }) => {
  const [query, setQuery] = useState('');
  const [providerType, setProviderType] = useState<'mock' | 'mock_partial' | 'ollama'>('mock');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [topK, setTopK] = useState(3);
  const [maxPassages, setMaxPassages] = useState(5);
  const [structuredOutput, setStructuredOutput] = useState(false);
  const [enableCompression, setEnableCompression] = useState(false);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || query.trim().length < 3 || isLoading) return;

    onSubmit({
      query: query.trim(),
      provider_type: providerType,
      top_k_judgments: topK,
      max_passages: maxPassages,
      structured_output: structuredOutput,
      enable_compression: enableCompression,
      enable_graph: false,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  };

  const applyPreset = (presetQuery: string, presetProvider: 'mock' | 'mock_partial' | 'ollama') => {
    setQuery(presetQuery);
    setProviderType(presetProvider);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
      {/* Demonstration Presets */}
      <div className="mb-4">
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          <span>Audit Demo Queries</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {CANONICAL_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => applyPreset(preset.query, preset.provider)}
              className="px-3 py-1.5 text-xs rounded-lg border border-slate-200 bg-slate-50 hover:bg-amber-50 hover:border-amber-300 text-slate-700 transition-colors text-left focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              <strong className="text-slate-900 block">{preset.label}</strong>
              <span className="text-[10px] text-slate-500">{preset.category}</span>
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="legal-query-input" className="block text-sm font-semibold text-slate-800 mb-1.5 font-serif">
            Enter Legal Inquiry / Case Law Proposition
          </label>
          <div className="relative">
            <textarea
              id="legal-query-input"
              rows={4}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="e.g. Can the rules of selection or eligibility criteria be changed after the recruitment process has commenced under Rajasthan High Court rules?"
              disabled={isLoading}
              className="w-full px-4 py-3 text-sm text-slate-900 bg-white border border-slate-300 rounded-lg shadow-inner focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent transition-all placeholder:text-slate-400 disabled:opacity-60 resize-y"
            />
          </div>
          <div className="flex items-center justify-between mt-1 text-xs text-slate-500">
            <span>Minimum 3 characters</span>
            <span>Press <kbd className="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-300 font-mono text-[10px]">Ctrl</kbd> + <kbd className="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-300 font-mono text-[10px]">Enter</kbd> to execute</span>
          </div>
        </div>

        {/* Controls row */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2 border-t border-slate-100">
          <div className="flex flex-wrap items-center gap-3">
            {/* Provider Selection */}
            <div className="flex items-center gap-2">
              <label htmlFor="provider-select" className="text-xs font-medium text-slate-600">
                Inference Provider:
              </label>
              <select
                id="provider-select"
                value={providerType}
                onChange={(e) => setProviderType(e.target.value as any)}
                disabled={isLoading}
                className="text-xs px-2.5 py-1.5 rounded-md border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-amber-500"
              >
                <option value="mock">Deterministic Mock (Fast Baseline)</option>
                <option value="mock_partial">Deterministic Mock (Missing Proviso / Partial)</option>
                <option value="ollama">Local Ollama (llama3.2:1b CPU)</option>
              </select>
            </div>

            {/* Advanced Options Toggle */}
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs flex items-center gap-1 text-slate-600 hover:text-slate-900 transition-colors py-1 px-2 rounded hover:bg-slate-100"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>{showAdvanced ? 'Hide Options' : 'Options'}</span>
            </button>
          </div>

          <button
            type="submit"
            disabled={isLoading || query.trim().length < 3}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
                <span>Verifying Evidence...</span>
              </>
            ) : (
              <>
                <Search className="w-4 h-4 text-amber-400" />
                <span>Verify Legal Query</span>
              </>
            )}
          </button>
        </div>

        {/* Collapsible Advanced Options */}
        {showAdvanced && (
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs mt-3">
            <div>
              <label htmlFor="top-k-input" className="block text-slate-700 font-medium mb-1">
                Top Judgments (k): {topK}
              </label>
              <input
                id="top-k-input"
                type="range"
                min="1"
                max="10"
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="w-full accent-amber-500"
              />
            </div>
            <div>
              <label htmlFor="max-passages-input" className="block text-slate-700 font-medium mb-1">
                Max Passages: {maxPassages}
              </label>
              <input
                id="max-passages-input"
                type="range"
                min="1"
                max="10"
                value={maxPassages}
                onChange={(e) => setMaxPassages(Number(e.target.value))}
                className="w-full accent-amber-500"
              />
            </div>
            <div className="flex items-center gap-2 pt-3">
              <input
                type="checkbox"
                id="structured-output-check"
                checked={structuredOutput}
                onChange={(e) => setStructuredOutput(e.target.checked)}
                className="rounded text-amber-600 focus:ring-amber-500"
              />
              <label htmlFor="structured-output-check" className="text-slate-700 font-medium cursor-pointer">
                JSON Structured Claims
              </label>
            </div>
            <div className="flex items-center gap-2 pt-3">
              <input
                type="checkbox"
                id="compression-check"
                checked={enableCompression}
                onChange={(e) => setEnableCompression(e.target.checked)}
                className="rounded text-amber-600 focus:ring-amber-500"
              />
              <label htmlFor="compression-check" className="text-slate-700 font-medium cursor-pointer">
                Context Compression
              </label>
            </div>
          </div>
        )}
      </form>
    </div>
  );
};

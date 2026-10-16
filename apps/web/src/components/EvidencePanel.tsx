import React, { useState } from 'react';
import { EvidencePassage } from '../types/rag';
import { BookOpen, Calendar, Hash, FileText, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';

interface EvidencePanelProps {
  passages: EvidencePassage[];
  highlightedId?: string | null;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({ passages, highlightedId }) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedAll, setExpandedAll] = useState(true);
  const [collapsedIds, setCollapsedIds] = useState<Record<string, boolean>>({});

  const toggleCollapse = (id: string) => {
    setCollapsedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const copyPassage = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (!passages || passages.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 text-center text-slate-500 text-sm">
        <BookOpen className="w-8 h-8 text-slate-300 mx-auto mb-2" />
        <p>No judicial evidence passages were retrieved for this query.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="p-4 sm:p-5 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-amber-600" />
          <h3 className="text-sm font-bold text-slate-900 font-serif">
            Verified Judicial Evidence Passages ({passages.length})
          </h3>
        </div>
        <button
          type="button"
          onClick={() => {
            const nextState = !expandedAll;
            setExpandedAll(nextState);
            const newCollapsed: Record<string, boolean> = {};
            passages.forEach((p) => {
              newCollapsed[p.evidence_id] = !nextState;
            });
            setCollapsedIds(newCollapsed);
          }}
          className="text-xs text-slate-600 hover:text-slate-900 font-medium"
        >
          {expandedAll ? 'Collapse All' : 'Expand All'}
        </button>
      </div>

      <div className="p-4 sm:p-5 space-y-4">
        {passages.map((passage) => {
          const isHighlighted = highlightedId === passage.evidence_id;
          const isCollapsed = collapsedIds[passage.evidence_id] ?? false;

          return (
            <div
              key={passage.evidence_id}
              id={`evidence-${passage.evidence_id}`}
              className={`rounded-lg border transition-all ${
                isHighlighted
                  ? 'border-amber-400 bg-amber-50/40 ring-2 ring-amber-300 shadow-md'
                  : 'border-slate-200 bg-slate-50/50 hover:bg-slate-50'
              }`}
            >
              {/* Passage Card Header */}
              <div className="p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center justify-center px-2 py-0.5 rounded bg-amber-600 text-white font-mono font-bold text-xs">
                    [{passage.evidence_id}]
                  </span>
                  <h4 className="text-sm font-semibold text-slate-900 font-serif line-clamp-1">
                    {passage.case_title || 'Supreme Court Judgment'}
                  </h4>
                </div>

                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                  {passage.citation && (
                    <span className="px-2 py-0.5 rounded bg-slate-200 font-mono text-[11px]">
                      {passage.citation}
                    </span>
                  )}
                  {passage.structural_label && (
                    <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-mono text-[11px]">
                      {passage.structural_label}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => toggleCollapse(passage.evidence_id)}
                    className="p-1 hover:bg-slate-200 rounded text-slate-500"
                    title={isCollapsed ? 'Expand passage' : 'Collapse passage'}
                  >
                    {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Passage Meta info */}
              <div className="px-3 sm:px-4 py-2 bg-white text-[11px] text-slate-500 border-b border-slate-100 flex flex-wrap items-center gap-y-1 gap-x-4">
                <span className="flex items-center gap-1 font-mono">
                  <Hash className="w-3 h-3 text-slate-400" />
                  Doc ID: {passage.document_id}
                </span>
                {passage.decision_date && (
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3 text-slate-400" />
                    Decided: {passage.decision_date}
                  </span>
                )}
                <span className="flex items-center gap-1 font-mono">
                  <FileText className="w-3 h-3 text-slate-400" />
                  Character Span: [{passage.start_char}:{passage.end_char}] ({passage.end_char - passage.start_char} chars)
                </span>
              </div>

              {/* Passage Text Content */}
              {!isCollapsed && (
                <div className="p-3 sm:p-4 bg-white rounded-b-lg">
                  <blockquote className="text-xs sm:text-sm text-slate-800 font-serif leading-relaxed italic border-l-2 border-amber-300 pl-3">
                    &ldquo;{passage.passage_text}&rdquo;
                  </blockquote>
                  <div className="mt-3 flex justify-end">
                    <button
                      type="button"
                      onClick={() => copyPassage(passage.evidence_id, passage.passage_text)}
                      className="inline-flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-800 transition-colors"
                    >
                      {copiedId === passage.evidence_id ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-600" />
                          <span className="text-emerald-700">Copied to clipboard</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy passage</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

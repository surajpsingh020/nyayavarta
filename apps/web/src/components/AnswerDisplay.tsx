import React, { useState } from 'react';
import { RAGResult } from '../types/rag';
import { BadgeRenderer } from './BadgeRenderer';
import { Clock, ShieldAlert, Eye, EyeOff, Info, Cpu, Bot, HelpCircle } from 'lucide-react';

interface AnswerDisplayProps {
  result: RAGResult;
  onCitationClick?: (evidenceId: string) => void;
}

export const AnswerDisplay: React.FC<AnswerDisplayProps> = ({ result, onCitationClick }) => {
  const [showSuppressed, setShowSuppressed] = useState(false);

  const isRejected = result.verification_badge === 'rejected_answer';
  const isAbstention = result.verification_badge === 'insufficient_evidence' || result.status === 'insufficient_evidence';

  // Highlight citation brackets like [E1], [E2] in text
  const renderFormattedText = (text: string) => {
    const parts = text.split(/(\[E\d+\])/g);
    return parts.map((part, index) => {
      const match = part.match(/\[(E\d+)\]/);
      if (match) {
        const eid = match[1];
        return (
          <button
            key={index}
            type="button"
            onClick={() => onCitationClick?.(eid)}
            className="inline-flex items-center px-1.5 py-0.2 mx-0.5 text-xs font-mono font-bold rounded bg-amber-100 text-amber-900 border border-amber-300 hover:bg-amber-200 transition-colors cursor-pointer"
            title={`Jump to verified evidence passage ${eid}`}
          >
            {part}
          </button>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      {/* Header bar with badges */}
      <div className="p-4 sm:p-5 border-b border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <BadgeRenderer badge={result.verification_badge} size="md" />

          {/* Pipeline Status Tag */}
          <span className="text-xs px-2.5 py-1 rounded-full bg-slate-200/80 text-slate-700 font-mono">
            status: {result.status}
          </span>

          {/* Model / Provider Provenance */}
          {result.retrieval_metadata?.model_name ? (
            String(result.retrieval_metadata.model_name).toLowerCase().includes('mock') ? (
              <span
                data-testid="model-provenance"
                className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200 font-mono"
                title="Simulated mock inference provider"
              >
                <Cpu className="w-3.5 h-3.5 text-purple-500" />
                <span>Mock Provider ({result.retrieval_metadata.model_name})</span>
              </span>
            ) : (
              <span
                data-testid="model-provenance"
                className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-mono"
                title="Live local LLM inference provider"
              >
                <Bot className="w-3.5 h-3.5 text-emerald-600" />
                <span>Live Model ({result.retrieval_metadata.model_name})</span>
              </span>
            )
          ) : (
            <span
              data-testid="model-provenance"
              className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-slate-100 text-slate-500 border border-slate-200 font-mono"
              title="Model provenance metadata unavailable"
            >
              <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
              <span>Model information unavailable</span>
            </span>
          )}
        </div>

        {/* Latency timing */}
        {result.timing_ms && (
          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span>
              Total: {result.timing_ms.total_ms ? `${result.timing_ms.total_ms.toFixed(0)}ms` : 'N/A'}
              {result.timing_ms.retrieval_ms && ` (Retr: ${result.timing_ms.retrieval_ms.toFixed(0)}ms)`}
            </span>
          </div>
        )}
      </div>

      {/* Main answer body */}
      <div className="p-5 sm:p-6 space-y-4">
        {/* Contradicted / Rejected Suppression State */}
        {isRejected ? (
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-950 flex items-start gap-3">
              <ShieldAlert className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <h4 className="font-semibold text-sm text-red-900">
                  Unsafe Answer Suppressed by Verification Gate
                </h4>
                <p className="text-xs text-red-800 mt-1 leading-relaxed">
                  The generated answer was rejected because it contains ungrounded assertions or claims directly contradicted by cited Supreme Court authority.
                  In accordance with NyayaVarta&apos;s fail-closed safety policy, this text is suppressed to prevent reliance on incorrect legal doctrines.
                </p>
                <button
                  type="button"
                  onClick={() => setShowSuppressed(!showSuppressed)}
                  className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-red-800 hover:text-red-950 underline focus:outline-none"
                >
                  {showSuppressed ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  <span>{showSuppressed ? 'Hide Suppressed Text' : 'Inspect Suppressed Output (Audit Mode)'}</span>
                </button>
              </div>
            </div>

            {showSuppressed && (
              <div className="p-4 bg-slate-100 rounded-lg border border-slate-300 font-serif text-sm text-slate-700 italic border-dashed">
                <span className="not-italic text-xs font-mono uppercase tracking-wider text-slate-500 block mb-1">
                  [Suppressed Candidate Output]:
                </span>
                {renderFormattedText(result.answer)}
              </div>
            )}
          </div>
        ) : isAbstention ? (
          <div className="p-4 rounded-lg bg-sky-50 border border-sky-200 text-sky-950 flex items-start gap-3">
            <Info className="w-5 h-5 text-sky-600 shrink-0 mt-0.5" />
            <div className="space-y-1 w-full">
              <h4 className="font-semibold text-sm text-sky-900">
                Judicial Corpus Abstention (Insufficient Grounding)
              </h4>
              <p className="text-xs text-sky-800 leading-relaxed font-serif">
                {result.answer}
              </p>
              <p className="text-[11px] text-sky-600 mt-2">
                Grounding State: <code className="bg-sky-100 px-1 py-0.5 rounded">{result.grounding_status}</code>
              </p>

              {/* Raw generation audit inspection if model output was sanitized to canonical abstention */}
              {result.retrieval_metadata?.raw_model_generation &&
                result.retrieval_metadata.raw_model_generation.trim() !== result.answer.trim() && (
                  <div className="pt-2 mt-2 border-t border-sky-200/60">
                    <button
                      type="button"
                      onClick={() => setShowSuppressed(!showSuppressed)}
                      className="inline-flex items-center gap-1.5 text-xs font-medium text-sky-800 hover:text-sky-950 underline focus:outline-none"
                    >
                      {showSuppressed ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      <span>{showSuppressed ? 'Hide Raw Model Output' : 'Inspect Raw Model Output (Audit Mode)'}</span>
                    </button>

                    {showSuppressed && (
                      <div className="mt-2 p-3 bg-white/90 rounded border border-sky-200 font-mono text-xs text-slate-700 whitespace-pre-wrap border-dashed">
                        <span className="font-sans font-semibold text-[11px] text-slate-500 block mb-1">
                          [Raw Model Generation — Unverified / Non-Authoritative]:
                        </span>
                        {result.retrieval_metadata.raw_model_generation}
                      </div>
                    )}
                  </div>
                )}
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <h3 className="text-xs uppercase tracking-wider font-semibold text-slate-500">
              Grounded Legal Answer
            </h3>
            <div className="text-slate-900 font-serif leading-relaxed text-base sm:text-lg bg-slate-50/50 p-4 rounded-lg border border-slate-100">
              {renderFormattedText(result.answer)}
            </div>
          </div>
        )}

        {/* Legal Disclaimer Footer */}
        {result.legal_disclaimer && (
          <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-500 italic">
            Note: {result.legal_disclaimer}
          </div>
        )}
      </div>
    </div>
  );
};

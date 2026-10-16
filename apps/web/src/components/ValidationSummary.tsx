import React from 'react';
import { CitationValidationResult } from '../types/rag';
import { CheckCircle2, XCircle, ShieldCheck, AlertCircle, Info, Minus } from 'lucide-react';

interface ValidationSummaryProps {
  validation: CitationValidationResult;
  isAbstention?: boolean;
}

export const ValidationSummary: React.FC<ValidationSummaryProps> = ({ validation, isAbstention = false }) => {
  if (!validation) return null;

  const isAbstained = isAbstention ||
    (validation.semantic_support_status === 'not_evaluated' &&
     validation.cited_source_ids.length === 0 &&
     (validation.validation_notes?.some(n => n.toLowerCase().includes('abstention')) ?? false));

  const checks = [
    {
      label: 'Citation Syntax',
      passed: validation.citation_syntax_valid,
      description: isAbstained
        ? 'N/A — No citations emitted in abstention'
        : 'Well-formed [E#] citation bracket notation',
      isNA: isAbstained,
    },
    {
      label: 'Citation Existence',
      passed: validation.citation_existence_valid,
      description: isAbstained
        ? 'N/A — No citations emitted in abstention'
        : 'Cited IDs exist in active retrieved context',
      isNA: isAbstained,
    },
    {
      label: 'Offset Integrity',
      passed: validation.evidence_integrity_valid,
      description: 'Exact [start_char:end_char] match in 2024 SCR corpus',
      isNA: false,
    },
    {
      label: 'Complete Attribution',
      passed: validation.attribution_complete,
      description: isAbstained
        ? 'N/A — System abstained from making claims'
        : 'Zero uncited substantive assertions',
      isNA: isAbstained,
    },
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 sm:p-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-slate-700" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 font-serif">
            Citation & Grounding Integrity Checks
          </h4>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
          Mechanical Checks Only — Not Semantic Legal Verification
        </span>
      </div>

      {isAbstained && (
        <div className="mb-3 p-3 bg-sky-50/70 border border-sky-200/80 rounded-lg text-xs text-sky-900 flex items-start gap-2">
          <Info className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Abstention Notice:</span> The system abstained due to insufficient evidence. Substantive legal claims were not evaluated or verified. Mechanical citation checks reflect that no unsupported affirmative claims were advanced.
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        {checks.map((check, idx) => {
          let cardStyle = 'bg-rose-50/50 border-rose-200 text-rose-950';
          let icon = <XCircle className="w-4 h-4 text-rose-600 shrink-0" />;

          if (check.isNA) {
            cardStyle = 'bg-slate-50/80 border-slate-200 text-slate-700';
            icon = <Minus className="w-4 h-4 text-slate-400 shrink-0" />;
          } else if (check.passed) {
            cardStyle = 'bg-emerald-50/50 border-emerald-200 text-emerald-950';
            icon = <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />;
          }

          return (
            <div
              key={idx}
              className={`p-3 rounded-lg border flex flex-col justify-between ${cardStyle}`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold">{check.label}</span>
                {icon}
              </div>
              <p className="text-[11px] text-slate-600 leading-tight">{check.description}</p>
            </div>
          );
        })}
      </div>

      {/* Explicit distinction between mechanical integrity checks and semantic legal verification */}
      <div className="mt-3 pt-3 border-t border-slate-100 text-[11px] text-slate-500 flex flex-col sm:flex-row sm:items-center justify-between gap-1">
        <span>
          <strong>Distinction:</strong> Mechanical checks verify syntax, reference existence, and source offsets. Semantic legal correctness is established only through substantive judicial claim verification.
        </span>
      </div>

      {validation.validation_notes && validation.validation_notes.length > 0 && (
        <div className="mt-2 pt-2 border-t border-slate-100 text-xs text-slate-600 space-y-1">
          {validation.validation_notes.map((note, idx) => (
            <p key={idx} className="flex items-start gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
              <span>{note}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
};

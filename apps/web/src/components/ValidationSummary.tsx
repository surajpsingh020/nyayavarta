import React from 'react';
import { CitationValidationResult } from '../types/rag';
import { CheckCircle2, XCircle, ShieldCheck, AlertCircle } from 'lucide-react';

interface ValidationSummaryProps {
  validation: CitationValidationResult;
}

export const ValidationSummary: React.FC<ValidationSummaryProps> = ({ validation }) => {
  if (!validation) return null;

  const checks = [
    {
      label: 'Citation Syntax',
      passed: validation.citation_syntax_valid,
      description: 'Well-formed [E#] citation bracket notation',
    },
    {
      label: 'Citation Existence',
      passed: validation.citation_existence_valid,
      description: 'Cited IDs exist in active retrieved context',
    },
    {
      label: 'Offset Integrity',
      passed: validation.evidence_integrity_valid,
      description: 'Exact [start_char:end_char] match in 2024 SCR corpus',
    },
    {
      label: 'Complete Attribution',
      passed: validation.attribution_complete,
      description: 'Zero uncited substantive assertions',
    },
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 sm:p-5">
      <div className="flex items-center gap-2 mb-3">
        <ShieldCheck className="w-4 h-4 text-slate-700" />
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 font-serif">
          Citation & Grounding Integrity Checks
        </h4>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        {checks.map((check, idx) => (
          <div
            key={idx}
            className={`p-3 rounded-lg border flex flex-col justify-between ${
              check.passed
                ? 'bg-emerald-50/50 border-emerald-200 text-emerald-950'
                : 'bg-rose-50/50 border-rose-200 text-rose-950'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold">{check.label}</span>
              {check.passed ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
              )}
            </div>
            <p className="text-[11px] text-slate-600 leading-tight">{check.description}</p>
          </div>
        ))}
      </div>

      {validation.validation_notes && validation.validation_notes.length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-100 text-xs text-slate-600 space-y-1">
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

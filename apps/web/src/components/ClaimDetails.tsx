import React, { useState } from 'react';
import { ClaimAttribution, ClaimVerificationStatus } from '../types/rag';
import {
  ShieldCheck,
  AlertTriangle,
  HelpCircle,
  ShieldAlert,
  ChevronDown,
  ChevronRight,
  Sparkles,
} from 'lucide-react';

interface ClaimDetailsProps {
  claims: ClaimAttribution[];
}

const CLAIM_STATUS_CONFIG: Record<
  ClaimVerificationStatus,
  {
    label: string;
    badgeClass: string;
    Icon: React.ComponentType<{ className?: string }>;
  }
> = {
  supported: {
    label: 'Supported',
    badgeClass: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    Icon: ShieldCheck,
  },
  partially_supported: {
    label: 'Partially Supported',
    badgeClass: 'bg-amber-100 text-amber-900 border-amber-300',
    Icon: AlertTriangle,
  },
  unsupported: {
    label: 'Unsupported',
    badgeClass: 'bg-orange-100 text-orange-900 border-orange-300',
    Icon: AlertTriangle,
  },
  contradicted: {
    label: 'Contradicted',
    badgeClass: 'bg-red-100 text-red-900 border-red-300',
    Icon: ShieldAlert,
  },
  not_evaluated: {
    label: 'Not Evaluated',
    badgeClass: 'bg-slate-100 text-slate-800 border-slate-300',
    Icon: HelpCircle,
  },
};

export const ClaimDetails: React.FC<ClaimDetailsProps> = ({ claims }) => {
  const [isOpen, setIsOpen] = useState(true);

  if (!claims || claims.length === 0) {
    return null;
  }

  const supportedCount = claims.filter((c) => c.verification_status === 'supported').length;
  const partialCount = claims.filter((c) => c.verification_status === 'partially_supported').length;
  const contraCount = claims.filter((c) => c.verification_status === 'contradicted').length;
  const unsuppCount = claims.filter((c) => c.verification_status === 'unsupported').length;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-4 sm:p-5 border-b border-slate-100 bg-slate-50 flex items-center justify-between text-left hover:bg-slate-100/70 transition-colors"
      >
        <div className="flex items-center gap-2">
          {isOpen ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
          <Sparkles className="w-4 h-4 text-amber-600" />
          <h3 className="text-sm font-bold text-slate-900 font-serif">
            Substantive Claim Verification Audit ({claims.length} claims)
          </h3>
        </div>

        {/* Quick Counts Pill */}
        <div className="flex items-center gap-1.5 text-xs">
          {supportedCount > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-medium">
              {supportedCount} Supported
            </span>
          )}
          {partialCount > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-medium">
              {partialCount} Partial
            </span>
          )}
          {contraCount > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-800 font-medium">
              {contraCount} Contradicted
            </span>
          )}
          {unsuppCount > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-orange-100 text-orange-800 font-medium">
              {unsuppCount} Unsupported
            </span>
          )}
        </div>
      </button>

      {isOpen && (
        <div className="divide-y divide-slate-100">
          {claims.map((claim, idx) => {
            const statusConfig =
              CLAIM_STATUS_CONFIG[claim.verification_status] || CLAIM_STATUS_CONFIG.not_evaluated;
            const { label, badgeClass, Icon } = statusConfig;

            return (
              <div key={idx} className="p-4 sm:p-5 space-y-2 hover:bg-slate-50/50 transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-slate-400">#{idx + 1}</span>
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-semibold border ${badgeClass}`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span>{label}</span>
                    </span>
                    {claim.verification_method && (
                      <span className="text-[11px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                        {claim.verification_method}
                      </span>
                    )}
                  </div>

                  {claim.cited_evidence_ids && claim.cited_evidence_ids.length > 0 && (
                    <div className="flex items-center gap-1 text-xs">
                      <span className="text-slate-500">Cited:</span>
                      {claim.cited_evidence_ids.map((eid) => (
                        <span
                          key={eid}
                          className="px-1.5 py-0.2 rounded bg-amber-100 text-amber-900 border border-amber-300 font-mono font-bold text-[11px]"
                        >
                          [{eid}]
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <p className="text-sm font-serif text-slate-900 leading-relaxed pl-4 border-l-2 border-slate-300">
                  {claim.sentence}
                </p>

                {claim.verification_reason && (
                  <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded border border-slate-100">
                    <strong className="text-slate-700">Audit Finding:</strong> {claim.verification_reason}
                  </p>
                )}

                {claim.unresolved_uncertainty && (
                  <p className="text-xs text-amber-800 bg-amber-50 p-2.5 rounded border border-amber-200">
                    <strong className="text-amber-900">Unresolved Nuance:</strong> {claim.unresolved_uncertainty}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

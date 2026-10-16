import React from 'react';
import { VerificationBadge } from '../types/rag';
import {
  ShieldCheck,
  AlertTriangle,
  HelpCircle,
  ShieldAlert,
  BookOpen,
  XCircle,
} from 'lucide-react';

interface BadgeRendererProps {
  badge: VerificationBadge;
  size?: 'sm' | 'md' | 'lg';
  showDescription?: boolean;
}

export const BADGE_CONFIG: Record<
  VerificationBadge,
  {
    label: string;
    description: string;
    bgClass: string;
    textClass: string;
    borderClass: string;
    Icon: React.ComponentType<{ className?: string }>;
  }
> = {
  verified_supported: {
    label: 'Verified Legal Authority',
    description:
      'All substantive claims are affirmatively supported by direct, verified judicial authority from canonical Supreme Court judgments.',
    bgClass: 'bg-emerald-50 text-emerald-800',
    textClass: 'text-emerald-800',
    borderClass: 'border-emerald-300',
    Icon: ShieldCheck,
  },
  qualified_answer: {
    label: 'Qualified Answer',
    description:
      'One or more claims are partially supported or subject to unstated statutory conditions, exceptions, or caveats.',
    bgClass: 'bg-amber-50 text-amber-900',
    textClass: 'text-amber-900',
    borderClass: 'border-amber-300',
    Icon: AlertTriangle,
  },
  unverified_answer: {
    label: 'Unverified Legal Entailment',
    description:
      'Syntactic citation references exist, but deterministic semantic legal entailment could not be established. Must not be treated as authoritative.',
    bgClass: 'bg-slate-100 text-slate-800',
    textClass: 'text-slate-800',
    borderClass: 'border-slate-300',
    Icon: HelpCircle,
  },
  rejected_answer: {
    label: 'Answer Rejected / Contradicted',
    description:
      'Contains substantive claims contradicted by cited judicial authority or completely unsupported legal assertions. Answer content is flagged or suppressed.',
    bgClass: 'bg-red-50 text-red-900',
    textClass: 'text-red-900',
    borderClass: 'border-red-300',
    Icon: ShieldAlert,
  },
  insufficient_evidence: {
    label: 'Insufficient Corpus Evidence',
    description:
      'The grounding gate or retriever determined that available 2024 Supreme Court judgments do not establish the requested legal proposition. Clean system abstention.',
    bgClass: 'bg-sky-50 text-sky-900',
    textClass: 'text-sky-900',
    borderClass: 'border-sky-300',
    Icon: BookOpen,
  },
  system_error: {
    label: 'Infrastructure / Provider Error',
    description:
      'Backend provider timeout (HTTP 504) or local LLM failure (HTTP 503). Clearly distinct from a substantive legal abstention.',
    bgClass: 'bg-rose-50 text-rose-900',
    textClass: 'text-rose-900',
    borderClass: 'border-rose-300',
    Icon: XCircle,
  },
};

export const BadgeRenderer: React.FC<BadgeRendererProps> = ({
  badge,
  size = 'md',
  showDescription = false,
}) => {
  const config = BADGE_CONFIG[badge] || BADGE_CONFIG.unverified_answer;
  const { label, description, bgClass, borderClass, Icon } = config;

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-xs font-medium gap-1',
    md: 'px-3 py-1 text-sm font-semibold gap-1.5',
    lg: 'px-4 py-2 text-base font-bold gap-2',
  }[size];

  const iconSizes = {
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  }[size];

  return (
    <div className="inline-flex flex-col gap-1">
      <div
        data-testid={`badge-${badge}`}
        className={`inline-flex items-center rounded-md border shadow-sm ${sizeStyles} ${bgClass} ${borderClass}`}
        role="status"
        aria-label={`Verification Status: ${label}`}
      >
        <Icon className={`${iconSizes} shrink-0`} />
        <span>{label}</span>
      </div>
      {showDescription && (
        <p className="text-xs text-slate-600 mt-0.5 max-w-xl">{description}</p>
      )}
    </div>
  );
};

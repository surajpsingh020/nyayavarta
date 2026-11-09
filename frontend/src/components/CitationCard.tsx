'use client';

import React, { useState } from 'react';
import { Scale, ChevronDown, ChevronUp, BookOpen, AlertCircle } from 'lucide-react';
import { Citation } from '@/lib/api';

interface CitationCardProps {
  citations: Citation[];
  className?: string;
}

export default function CitationCard({ citations, className = '' }: CitationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!citations || citations.length === 0) {
    return null;
  }

  const displayedCitations = isExpanded ? citations : citations.slice(0, 2);

  return (
    <div className={`mt-3 bg-amber-50/70 border border-amber-200/80 rounded-xl p-3.5 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-amber-700 flex-shrink-0" />
          <span className="text-xs font-bold text-amber-900 tracking-wide uppercase">
            Legal Citations & Law Mapping ({citations.length})
          </span>
        </div>
        {citations.length > 2 && (
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1 text-xs font-semibold text-amber-800 hover:text-amber-950 transition-colors"
          >
            {isExpanded ? (
              <>
                Show Less <ChevronUp className="w-3.5 h-3.5" />
              </>
            ) : (
              <>
                Show All ({citations.length}) <ChevronDown className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        )}
      </div>

      <div className="mt-2.5 space-y-2">
        {displayedCitations.map((cit, idx) => (
          <div
            key={idx}
            className="bg-white/90 border border-amber-100 rounded-lg p-2.5 text-xs shadow-2xs"
          >
            <div className="flex items-start justify-between gap-2">
              <span className="font-semibold text-gray-900 flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-primary-600 flex-shrink-0" />
                {cit.section}
              </span>
              <span className="bg-amber-100 text-amber-800 text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap">
                {cit.subject || 'Statute'}
              </span>
            </div>
            {cit.key_changes && (
              <p className="mt-1 text-gray-600 text-[11px] leading-relaxed pl-5">
                <span className="font-medium text-gray-700">Transition / Notes: </span>
                {cit.key_changes}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

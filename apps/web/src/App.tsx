import React, { useState, useRef } from 'react';
import { Header } from './components/Header';
import { LegalDisclaimer } from './components/LegalDisclaimer';
import { QueryInput } from './components/QueryInput';
import { AnswerDisplay } from './components/AnswerDisplay';
import { EvidencePanel } from './components/EvidencePanel';
import { ClaimDetails } from './components/ClaimDetails';
import { ValidationSummary } from './components/ValidationSummary';
import { StatusBanner } from './components/StatusBanner';
import { RAGQueryRequest, RAGResult } from './types/rag';
import { queryRag } from './services/api';
import { Scale } from 'lucide-react';

export const App: React.FC = () => {
  const [result, setResult] = useState<RAGResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [highlightedId, setHighlightedId] = useState<string | null>(null);

  const resultsRef = useRef<HTMLDivElement>(null);

  const handleQuerySubmit = async (params: RAGQueryRequest) => {
    setIsLoading(true);
    setError(null);
    setHighlightedId(null);

    try {
      const data = await queryRag(params);
      setResult(data);

      // Scroll to results
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    } catch (err: any) {
      setError(err);
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCitationClick = (evidenceId: string) => {
    setHighlightedId(evidenceId);
    const targetElement = document.getElementById(`evidence-${evidenceId}`);
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  return (
    <div className="min-h-screen bg-slate-100/70 text-slate-900 flex flex-col font-sans">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6">
        <LegalDisclaimer />

        {/* Query Input Card */}
        <section aria-label="Legal Inquiry Form">
          <QueryInput onSubmit={handleQuerySubmit} isLoading={isLoading} />
        </section>

        {/* Error banner */}
        <StatusBanner error={error} onDismiss={() => setError(null)} />

        {/* Results Section */}
        {result && (
          <section ref={resultsRef} className="space-y-6" aria-label="Verification Results">
            {/* Answer Card */}
            <AnswerDisplay result={result} onCitationClick={handleCitationClick} />

            {/* Validation & Grounding Metrics */}
            <ValidationSummary validation={result.citation_validation} />

            {/* Claim-by-Claim Verification Audit */}
            {result.claims && result.claims.length > 0 && (
              <ClaimDetails claims={result.claims} />
            )}

            {/* Judicial Evidence Panel */}
            <EvidencePanel
              passages={result.evidence_passages}
              highlightedId={highlightedId}
            />
          </section>
        )}

        {/* Empty state when no result and not loading */}
        {!result && !isLoading && !error && (
          <div className="text-center py-12 px-4 rounded-xl border border-dashed border-slate-300 bg-white/60">
            <Scale className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-700 font-serif">
              Ready for Judicial Legal Research
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 leading-relaxed">
              Enter a legal proposition or click any of the 4 demonstration query presets above to test evidence grounding, citation verification, and answer-level badges.
            </p>
          </div>
        )}
      </main>

      <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 space-y-1">
          <p className="font-serif text-slate-700 font-medium">
            NyayaVarta (न्यायवार्ता) — Supreme Court of India Evidence-Grounded Legal AI Platform
          </p>
          <p>
            Application software licensed under MIT. Analyzed Supreme Court judgments are public judicial records; citation and research reproduction reference Section 52(1)(q)(iv) of the Indian Copyright Act, 1957. Third-party judicial texts and law reports remain subject to their respective provenance and publication terms.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;

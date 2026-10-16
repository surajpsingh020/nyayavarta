import { AlertTriangle } from 'lucide-react';

export const LegalDisclaimer: React.FC = () => {
  return (
    <div className="bg-amber-500/10 border-l-4 border-amber-500 p-4 rounded-r-lg text-amber-900 text-xs sm:text-sm">
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-amber-950">
            Academic Research Prototype — Not for Real-World Legal Practice
          </p>
          <p className="text-amber-800 leading-relaxed">
            NyayaVarta is an artificial intelligence research platform designed to investigate evidence grounding and citation verification over Indian Supreme Court judgments.
            Outputs <strong>do not constitute legal advice, professional representation, or certified case law verification</strong>.
            Citations reflect observational text in the 2024 SCR corpus; the system does not independently verify whether cited precedents remain good law or have been overruled by larger benches.
          </p>
        </div>
      </div>
    </div>
  );
};

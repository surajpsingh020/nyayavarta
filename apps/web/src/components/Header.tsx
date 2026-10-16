import React, { useEffect, useState } from 'react';
import { Scale, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { checkHealth } from '../services/api';

export const Header: React.FC = () => {
  const [health, setHealth] = useState<{ status: string; environment: string } | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  const fetchHealth = async () => {
    setIsChecking(true);
    try {
      const data = await checkHealth();
      setHealth(data);
    } catch {
      setHealth(null);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    checkHealth()
      .then((data) => {
        if (isMounted) setHealth(data);
      })
      .catch(() => {
        if (isMounted) setHealth(null);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <header className="bg-slate-900 text-white border-b border-slate-800 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-lg border border-amber-500/20 shadow-inner">
              <Scale className="w-8 h-8" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-white font-serif">
                  NyayaVarta <span className="text-amber-400 font-normal text-xl">(न्यायवार्ता)</span>
                </h1>
                <span className="text-xs uppercase tracking-wider px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 font-semibold border border-blue-500/30">
                  Demo Prototype
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Evidence-Grounded Legal Research Assistant for Supreme Court of India Judgments (2024 SCR)
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs">
            {/* Release Gate Badge */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300">
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              <span>Gate: <strong className="text-amber-300">HOLD (Pending Legal Review)</strong></span>
            </div>

            {/* Backend Health Status */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 border border-slate-700">
              {health ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-300 font-medium">API Connected ({health.environment})</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                  <span className="text-rose-300 font-medium">API Disconnected</span>
                </>
              )}
              <button
                onClick={fetchHealth}
                disabled={isChecking}
                aria-label="Refresh API connection"
                className="text-slate-400 hover:text-white transition-colors ml-1 p-0.5 rounded hover:bg-slate-700 disabled:opacity-50"
                title="Refresh API connection"
              >
                <RefreshCw className={`w-3 h-3 ${isChecking ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

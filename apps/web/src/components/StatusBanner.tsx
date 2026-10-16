import React from 'react';
import { AlertCircle, Clock, ServerOff, XCircle } from 'lucide-react';
import { ApiError } from '../services/api';

interface StatusBannerProps {
  error: Error | null;
  onDismiss?: () => void;
}

export const StatusBanner: React.FC<StatusBannerProps> = ({ error, onDismiss }) => {
  if (!error) return null;

  const isTimeout = error instanceof ApiError && error.status === 504;
  const isUnavailable = error instanceof ApiError && error.status === 503;
  const isConnection = error instanceof ApiError && error.status === 0;

  return (
    <div
      role="alert"
      className="rounded-xl border border-rose-300 bg-rose-50 p-4 sm:p-5 text-rose-950 shadow-sm"
    >
      <div className="flex items-start gap-3">
        {isTimeout ? (
          <Clock className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
        ) : isUnavailable || isConnection ? (
          <ServerOff className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
        ) : (
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
        )}

        <div className="flex-1 space-y-1">
          <h4 className="text-sm font-bold text-rose-900">
            {isTimeout
              ? 'Request Timed Out (HTTP 504)'
              : isUnavailable
              ? 'Local LLM Unavailable (HTTP 503)'
              : isConnection
              ? 'Backend Connection Failed'
              : 'API Request Error'}
          </h4>
          <p className="text-xs sm:text-sm text-rose-800 leading-relaxed font-sans">
            {error.message}
          </p>

          {(isTimeout || isUnavailable) && (
            <div className="mt-2 text-xs text-rose-700 bg-rose-100/60 p-2 rounded border border-rose-200">
              <strong>Tip:</strong> You can select <em>&quot;Deterministic Mock (Fast Baseline)&quot;</em> in the provider dropdown above to execute reproducible CPU evaluation without relying on a local LLM daemon.
            </div>
          )}
        </div>

        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss error"
            className="text-rose-400 hover:text-rose-700 p-1 rounded-md transition-colors"
          >
            <XCircle className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};

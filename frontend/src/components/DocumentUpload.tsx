'use client';

import React, { useRef, useState } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { uploadDocument, UploadResponse } from '@/lib/api';

interface DocumentUploadProps {
  onUploadSuccess?: (res: UploadResponse) => void;
  className?: string;
}

export default function DocumentUpload({ onUploadSuccess, className = '' }: DocumentUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{
    type: 'success' | 'error';
    text: string;
    chunks?: number;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileProcess = async (file: File) => {
    // Validate file extension
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    const allowed = ['.pdf', '.docx', '.doc', '.txt'];
    if (!allowed.includes(ext)) {
      setStatusMessage({
        type: 'error',
        text: `Invalid file format (${ext}). Supported: PDF, DOCX, TXT.`,
      });
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      setStatusMessage({
        type: 'error',
        text: 'File exceeds 20MB limit.',
      });
      return;
    }

    setIsUploading(true);
    setStatusMessage(null);

    try {
      const response = await uploadDocument(file);
      setStatusMessage({
        type: 'success',
        text: response.message || `Successfully indexed "${response.filename}".`,
        chunks: response.chunks_created,
      });
      onUploadSuccess?.(response);
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to upload document. Please ensure backend is reachable.',
      });
    } finally {
      setIsUploading(false);
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => {
    setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileProcess(e.dataTransfer.files[0]);
    }
  };

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileProcess(e.target.files[0]);
    }
  };

  return (
    <div className={`card ${className}`}>
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-5 h-5 text-primary-600" />
        <h3 className="font-semibold text-gray-800 text-base">
          Legal Document Ingestion (दस्तावेज़ अपलोड)
        </h3>
      </div>
      <p className="text-xs text-gray-500 mb-4 leading-relaxed">
        Upload legal filings, FIR copies, petitions, or contracts (PDF, DOCX, TXT up to 20MB).
        Our PyMuPDF engine extracts and indexes chunks dynamically into your RAG pipeline.
      </p>

      {/* Drag & Drop Zone */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
          isDragging
            ? 'border-primary-500 bg-primary-50/80 scale-[1.01]'
            : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50/70'
        } ${isUploading ? 'opacity-60 pointer-events-none' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.doc,.txt"
          onChange={onInputChange}
          className="hidden"
          aria-label="Upload document file"
        />

        <div className="flex flex-col items-center justify-center space-y-2">
          {isUploading ? (
            <div className="flex flex-col items-center">
              <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
              <p className="text-xs font-semibold text-primary-700 mt-2">
                Extracting text and chunking into Neo4j Knowledge Graph & BM25...
              </p>
            </div>
          ) : (
            <>
              <div className="w-12 h-12 rounded-full bg-primary-100/80 flex items-center justify-center text-primary-600 mb-1">
                <UploadCloud className="w-6 h-6" />
              </div>
              <p className="text-sm font-medium text-gray-700">
                Click to browse or drag and drop files here
              </p>
              <p className="text-[11px] text-gray-400">
                PDF, Word (.docx) or plain text (.txt)
              </p>
            </>
          )}
        </div>
      </div>

      {/* Status Alert */}
      {statusMessage && (
        <div
          className={`mt-3 p-3 rounded-xl flex items-start gap-2.5 text-xs ${
            statusMessage.type === 'success'
              ? 'bg-green-50 border border-green-200 text-green-800'
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}
        >
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
          )}
          <div>
            <span className="font-semibold">{statusMessage.text}</span>
            {statusMessage.chunks !== undefined && (
              <p className="text-[11px] text-green-700 mt-0.5">
                {statusMessage.chunks} search chunks indexed and ready for retrieval.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

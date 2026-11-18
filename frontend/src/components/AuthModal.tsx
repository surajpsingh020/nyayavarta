'use client';

import React, { useState } from 'react';
import {
  X,
  Lock,
  Mail,
  User,
  LogIn,
  UserPlus,
  Loader2,
  AlertCircle,
  ShieldCheck,
  Scale,
} from 'lucide-react';
import { loginUser, registerUser, UserInfo } from '@/lib/api';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: UserInfo) => void;
  initialMode?: 'login' | 'signup';
}

export default function AuthModal({
  isOpen,
  onClose,
  onSuccess,
  initialMode = 'login',
}: AuthModalProps) {
  const [mode, setMode] = useState<'login' | 'signup'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setErrorMsg('Please enter a valid email address.');
      return;
    }

    if (password.length < 6) {
      setErrorMsg('Password must be at least 6 characters long.');
      return;
    }

    if (mode === 'signup') {
      if (!fullName.trim()) {
        setErrorMsg('Please enter your full name.');
        return;
      }
      if (password !== confirmPassword) {
        setErrorMsg('Passwords do not match.');
        return;
      }
    }

    setIsLoading(true);
    try {
      if (mode === 'login') {
        const res = await loginUser(cleanEmail, password);
        onSuccess(res.user);
        onClose();
      } else {
        const res = await registerUser(cleanEmail, password, fullName.trim());
        onSuccess(res.user);
        onClose();
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden">
        {/* Modal Header */}
        <div className="bg-gradient-to-r from-primary-900 to-primary-800 text-white p-6 pb-5 relative">
          <button
            type="button"
            onClick={onClose}
            className="absolute top-4 right-4 text-gray-300 hover:text-white p-1 rounded-lg transition-colors"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-accent-500/20 border border-accent-400/30 flex items-center justify-center text-accent-300">
              <Scale className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold">
                {mode === 'login' ? 'लॉग इन (Log In)' : 'नया खाता बनाएं (Sign Up)'}
              </h2>
              <p className="text-xs text-gray-300">
                सुरक्षित एवं निजी कानूनी परामर्श (Private & Secure Legal Portal)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 text-[11px] text-accent-300 mt-2 bg-primary-950/40 px-2.5 py-1 rounded-lg border border-accent-400/20">
            <ShieldCheck className="w-3.5 h-3.5 flex-shrink-0" />
            <span>आपकी चैट और परामर्श इतिहास पूरी तरह गोपनीय व एन्क्रिप्टेड है।</span>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-gray-200 bg-gray-50/70">
          <button
            type="button"
            onClick={() => {
              setMode('login');
              setErrorMsg(null);
            }}
            className={`flex-1 py-3 text-xs font-bold transition-all border-b-2 flex items-center justify-center gap-1.5 ${
              mode === 'login'
                ? 'border-primary-600 text-primary-700 bg-white shadow-2xs'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            <LogIn className="w-4 h-4" />
            Log In (लॉग इन)
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('signup');
              setErrorMsg(null);
            }}
            className={`flex-1 py-3 text-xs font-bold transition-all border-b-2 flex items-center justify-center gap-1.5 ${
              mode === 'signup'
                ? 'border-primary-600 text-primary-700 bg-white shadow-2xs'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            <UserPlus className="w-4 h-4" />
            Sign Up (साइन अप)
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMsg && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2 text-xs text-red-700">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-600" />
              <span>{errorMsg}</span>
            </div>
          )}

          {mode === 'signup' && (
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-gray-700">
                Full Name (पूरा नाम)
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Ramesh Sharma"
                  className="w-full pl-9 pr-3 py-2 text-xs border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-600 transition-all"
                />
              </div>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-gray-700">
              Email Address (ईमेल पता)
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                className="w-full pl-9 pr-3 py-2 text-xs border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-600 transition-all"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-gray-700">
              Password (पासवर्ड)
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2 text-xs border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-600 transition-all"
              />
            </div>
            {mode === 'signup' && (
              <p className="text-[10px] text-gray-500">Minimum 6 characters</p>
            )}
          </div>

          {mode === 'signup' && (
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-gray-700">
                Confirm Password (पासवर्ड पुष्टि)
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-3 py-2 text-xs border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-600 transition-all"
                />
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 px-4 bg-primary-700 hover:bg-primary-800 disabled:bg-primary-400 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition-all mt-4 cursor-pointer"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>कृपया प्रतीक्षा करें... (Processing)</span>
              </>
            ) : mode === 'login' ? (
              <>
                <LogIn className="w-4 h-4" />
                <span>लॉग इन करें (Log In)</span>
              </>
            ) : (
              <>
                <UserPlus className="w-4 h-4" />
                <span>खाता बनाएं (Create Account)</span>
              </>
            )}
          </button>

          <div className="text-center pt-2">
            <button
              type="button"
              onClick={() => {
                setMode(mode === 'login' ? 'signup' : 'login');
                setErrorMsg(null);
              }}
              className="text-xs text-primary-700 hover:text-primary-800 font-semibold underline"
            >
              {mode === 'login'
                ? "Don't have an account? Sign Up (नया खाता बनाएं)"
                : 'Already have an account? Log In (पहले से खाता है? लॉग इन करें)'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

'use client';

import React from 'react';
import { User, GraduationCap, HeartHandshake, Briefcase } from 'lucide-react';
import { UserProfileType } from '@/lib/api';

interface ProfileOption {
  id: UserProfileType;
  label: string;
  hindiLabel: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

export const USER_PROFILES: ProfileOption[] = [
  {
    id: 'general',
    label: 'General Citizen',
    hindiLabel: 'आम नागरिक',
    description: 'Everyday rights, simple remedies, and immediate steps',
    icon: User,
  },
  {
    id: 'student',
    label: 'Student / Academic',
    hindiLabel: 'विद्यार्थी',
    description: 'Educational breakdown, statutory logic, and definitions',
    icon: GraduationCap,
  },
  {
    id: 'senior_citizen',
    label: 'Senior Citizen',
    hindiLabel: 'वरिष्ठ नागरिक',
    description: 'Compassionate, simple guidance and elder welfare rights',
    icon: HeartHandshake,
  },
  {
    id: 'professional',
    label: 'Professional',
    hindiLabel: 'पेशेवर',
    description: 'Formal compliance, procedural timelines, and liability',
    icon: Briefcase,
  },
];

interface ProfileSelectorProps {
  selectedProfile: UserProfileType;
  onProfileChange: (profile: UserProfileType) => void;
  className?: string;
}

export default function ProfileSelector({
  selectedProfile,
  onProfileChange,
  className = '',
}: ProfileSelectorProps) {
  return (
    <div className={`space-y-2 ${className}`}>
      <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500">
        User Persona / उपयोगकर्ता प्रोफ़ाइल
      </label>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        {USER_PROFILES.map((profile) => {
          const Icon = profile.icon;
          const isSelected = selectedProfile === profile.id;
          return (
            <button
              key={profile.id}
              type="button"
              onClick={() => onProfileChange(profile.id)}
              className={`flex flex-col text-left p-3 rounded-xl border-2 transition-all ${
                isSelected
                  ? 'border-primary-500 bg-primary-50/70 shadow-sm ring-2 ring-primary-100'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <div
                  className={`p-1.5 rounded-lg ${
                    isSelected ? 'bg-primary-500 text-white' : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                </div>
                <div>
                  <span className="text-xs font-bold text-primary-700 block leading-tight">
                    {profile.hindiLabel}
                  </span>
                  <span className="text-sm font-semibold text-gray-900 block leading-tight">
                    {profile.label}
                  </span>
                </div>
              </div>
              <p className="text-[11px] text-gray-500 line-clamp-2 mt-1">
                {profile.description}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

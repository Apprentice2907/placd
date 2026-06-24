import React from 'react';
import { Check } from 'lucide-react';

interface StepIndicatorProps {
  currentStep: number;
}

const steps = [
  { num: 1, label: 'Profile' },
  { num: 2, label: 'Job Target' },
  { num: 3, label: 'AI Analysis' },
  { num: 4, label: 'Preview' }
];

export const StepIndicator: React.FC<StepIndicatorProps> = ({ currentStep }) => {
  return (
    <div className="w-full py-6 mb-8 flex justify-between items-center no-print">
      <div className="flex w-full max-w-2xl mx-auto justify-between relative">
        {/* Connector line */}
        <div className="absolute top-4 left-0 w-full h-px bg-white/10 z-0" />
        {/* Active connector */}
        <div
          className="absolute top-4 left-0 h-px bg-gradient-to-r from-purple-500 to-purple-400 z-0 transition-all duration-700"
          style={{ width: `${((currentStep - 1) / (steps.length - 1)) * 100}%` }}
        />

        {steps.map((step) => {
          const isCompleted = currentStep > step.num;
          const isCurrent = currentStep === step.num;

          return (
            <div
              key={step.num}
              className="relative z-10 flex flex-col items-center gap-2.5"
              style={{ background: 'transparent' }}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-300 border
                  ${isCompleted
                    ? 'bg-purple-500 border-purple-500 text-white shadow-[0_0_12px_rgba(168,85,247,0.5)]'
                    : isCurrent
                    ? 'bg-[#0a0a0a] border-purple-500 text-purple-400 shadow-[0_0_12px_rgba(168,85,247,0.3)]'
                    : 'bg-[#0a0a0a] border-white/15 text-white/30'
                  }`}
              >
                {isCompleted ? <Check className="w-4 h-4" /> : step.num}
              </div>
              <span
                className={`text-xs font-medium tracking-wide transition-colors duration-300 ${
                  isCurrent
                    ? 'text-purple-400'
                    : isCompleted
                    ? 'text-white/80'
                    : 'text-white/30'
                }`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

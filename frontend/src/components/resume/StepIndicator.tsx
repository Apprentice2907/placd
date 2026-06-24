import React from 'react';
import { Check } from 'lucide-react';

interface StepIndicatorProps {
  currentStep: number;
}

const steps = [
  { num: 1, label: 'Profile' },
  { num: 2, label: 'Job Target' },
  { num: 3, label: 'AI Analysis' },
  { num: 4, label: 'Preview' },
];

export const StepIndicator: React.FC<StepIndicatorProps> = ({ currentStep }) => {
  return (
    <div className="w-full py-6 mb-8 flex justify-between items-center no-print">
      <div className="flex w-full max-w-2xl mx-auto justify-between relative">
        {/* Base connector */}
        <div className="absolute top-4 left-0 w-full h-px bg-gray-200 z-0" />
        {/* Active connector */}
        <div
          className="absolute top-4 left-0 h-px bg-violet-500 z-0 transition-all duration-700"
          style={{ width: `${((currentStep - 1) / (steps.length - 1)) * 100}%` }}
        />

        {steps.map(step => {
          const isCompleted = currentStep > step.num;
          const isCurrent = currentStep === step.num;

          return (
            <div key={step.num} className="relative z-10 flex flex-col items-center gap-2.5 bg-[#f8f9fa] px-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm border-2 transition-all duration-300 ${
                isCompleted
                  ? 'bg-violet-600 border-violet-600 text-white shadow-sm'
                  : isCurrent
                  ? 'bg-white border-violet-500 text-violet-600'
                  : 'bg-white border-gray-300 text-gray-400'
              }`}>
                {isCompleted ? <Check className="w-4 h-4" /> : step.num}
              </div>
              <span className={`text-xs font-medium tracking-wide transition-colors ${
                isCurrent ? 'text-violet-600' : isCompleted ? 'text-gray-700' : 'text-gray-400'
              }`}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

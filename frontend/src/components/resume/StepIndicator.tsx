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
    <div className="w-full py-4 border-b border-[var(--border-color)] mb-6 flex justify-between items-center no-print">
      <div className="flex w-full max-w-3xl mx-auto justify-between relative">
        <div className="absolute top-1/2 left-0 w-full h-0.5 bg-neutral-200 dark:bg-neutral-800 -translate-y-1/2 z-0" />
        {steps.map((step) => {
          const isCompleted = currentStep > step.num;
          const isCurrent = currentStep === step.num;
          return (
            <div key={step.num} className="relative z-10 flex flex-col items-center gap-2 bg-[var(--bg-background)] px-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm transition-colors border-2
                ${isCompleted ? 'bg-indigo-600 border-indigo-600 text-white' : 
                  isCurrent ? 'bg-white dark:bg-neutral-900 border-indigo-600 text-indigo-600 dark:text-indigo-400' : 
                  'bg-white dark:bg-neutral-900 border-neutral-300 dark:border-neutral-700 text-neutral-400'}`}>
                {isCompleted ? <Check className="w-4 h-4" /> : step.num}
              </div>
              <span className={`text-xs font-medium ${isCurrent ? 'text-indigo-600 dark:text-indigo-400' : isCompleted ? 'text-black dark:text-white' : 'text-neutral-400'}`}>
                {step.label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  );
};

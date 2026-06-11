import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface OverflowWarningProps {
  isOverflowing?: boolean;
}

export const OverflowWarning: React.FC<OverflowWarningProps> = ({ isOverflowing = true }) => {
  if (!isOverflowing) return null;
  
  return (
    <div className="bg-amber-50 border border-amber-200 text-amber-800 dark:bg-amber-900/30 dark:border-amber-800 dark:text-amber-400 p-4 rounded-lg flex gap-3 items-start my-4 print:hidden max-w-4xl mx-auto">
      <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5 text-amber-500" />
      <div>
        <h4 className="font-bold text-sm">Resume length warning</h4>
        <p className="text-xs mt-1">Your resume might be spilling over one page. Consider removing older experiences or switching to shorter original bullets to keep it concise.</p>
      </div>
    </div>
  );
};

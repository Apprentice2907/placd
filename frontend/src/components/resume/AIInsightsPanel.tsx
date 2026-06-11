import React from 'react';
import type { ResearchResult, RewriteResult, ResumeProfile } from '../../types/resume';
import { CheckCircle2, RefreshCw } from 'lucide-react';

interface AIInsightsPanelProps {
  research: ResearchResult | null;
  rewrite: RewriteResult | null;
  isRewriting: boolean;
  profile: ResumeProfile;
  onNext: () => void;
}

export const AIInsightsPanel: React.FC<AIInsightsPanelProps> = ({ research, rewrite, isRewriting, profile, onNext }) => {
  if (!research) {
    return <div className="text-center py-20 text-indigo-500 font-medium flex flex-col items-center gap-4"><RefreshCw className="w-8 h-8 animate-spin"/> Analyzing job target...</div>;
  }

  // Helper to check if a keyword is vaguely present in the profile (naive check)
  const profileStr = JSON.stringify(profile).toLowerCase();
  const hasKeyword = (kw: string) => profileStr.includes(kw.toLowerCase());

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in pb-10">
      <div className="flex items-center justify-between border-b border-neutral-200 pb-4">
        <h2 className="text-2xl font-bold">AI Insights</h2>
        {rewrite ? (
          <div className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 border border-green-200 dark:border-green-800 px-3 py-1 rounded-full font-bold text-sm flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4" /> {rewrite.match_score}% Match Expected
          </div>
        ) : (
          <div className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border border-amber-200 dark:border-amber-800 px-3 py-1 rounded-full font-bold text-sm flex items-center gap-2">
            <RefreshCw className="w-3 h-3 animate-spin"/> Rewriting bullets...
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="space-y-4">
          <h3 className="text-lg font-bold">Top Keywords Needed</h3>
          <div className="flex flex-wrap gap-2">
            {research.top_keywords?.map((kw, i) => {
              const present = hasKeyword(kw);
              return (
                <span key={i} className={`px-2.5 py-1 rounded-md text-xs font-mono border ${present ? 'bg-green-50 border-green-200 text-green-700 dark:bg-green-900/20 dark:text-green-400' : 'bg-neutral-100 border-neutral-200 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300 dark:border-neutral-700'}`}>
                  {kw} {present && '✓'}
                </span>
              );
            })}
          </div>
        </div>
        
        <div className="space-y-4">
          <h3 className="text-lg font-bold">Culture & Emphasis</h3>
          <ul className="list-disc pl-5 text-sm space-y-1">
            {research.culture_signals?.map((sig, i) => (
              <li key={i}>{sig}</li>
            ))}
          </ul>
          {research.emphasis_notes && (
            <p className="text-sm italic text-neutral-600 dark:text-neutral-400 bg-neutral-50 dark:bg-neutral-900 p-3 rounded-lg border border-neutral-200 dark:border-neutral-800">
              "{research.emphasis_notes}"
            </p>
          )}
        </div>
      </div>

      {rewrite && rewrite.missing_keywords?.length > 0 && (
        <div className="space-y-2 pt-4 border-t border-neutral-200">
          <h3 className="text-lg font-bold text-amber-600 dark:text-amber-500 flex items-center gap-2">Still Missing</h3>
          <p className="text-sm opacity-80">We couldn't naturally inject these into your existing experience. Consider adding them if you have the skills:</p>
          <div className="flex flex-wrap gap-2">
            {rewrite.missing_keywords.map((kw, i) => (
              <span key={i} className="px-2.5 py-1 rounded-md text-xs font-mono border bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800">
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex justify-end pt-8">
        <button 
          onClick={onNext} 
          disabled={isRewriting || !rewrite}
          className={`px-6 py-2.5 rounded-lg font-bold text-white transition-all ${isRewriting ? 'bg-neutral-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700 animate-pulse shadow-lg shadow-indigo-500/30'}`}
        >
          {isRewriting ? 'Wait for Rewrite...' : 'Review Optimized Resume →'}
        </button>
      </div>
    </div>
  );
};

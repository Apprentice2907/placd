import React from 'react';
import type { ResumeProfile } from '../../types/resume';
import { CheckCircle2, RefreshCw, AlertTriangle, TrendingUp } from 'lucide-react';

interface AIInsightsPanelProps {
  generateResult: any | null;
  isGenerating: boolean;
  profile: ResumeProfile;
  onNext: () => void;
}

export const AIInsightsPanel: React.FC<AIInsightsPanelProps> = ({ generateResult, isGenerating, onNext }) => {
  if (isGenerating) {
    return <div className="text-center py-20 text-indigo-500 font-medium flex flex-col items-center gap-4"><RefreshCw className="w-8 h-8 animate-spin"/> Generating tailored resume & insights...</div>;
  }

  if (!generateResult) return null;

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in pb-10">
      <div className="flex items-center justify-between border-b border-neutral-200 pb-4">
        <h2 className="text-2xl font-bold">AI Insights & ATS Analysis</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* ATS Score Card */}
        <div className="md:col-span-1 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-xl p-6 shadow-sm flex flex-col items-center justify-center text-center space-y-4">
          <h3 className="text-sm font-bold text-neutral-500 uppercase tracking-wider">ATS Score Improvement</h3>
          <div className="flex items-center gap-4">
            <div className="flex flex-col items-center">
              <span className="text-3xl font-black text-neutral-400">{generateResult.ats_score_before || 0}</span>
              <span className="text-xs font-semibold text-neutral-500">Before</span>
            </div>
            <TrendingUp className="w-8 h-8 text-green-500" />
            <div className="flex flex-col items-center">
              <span className="text-5xl font-black text-green-600 dark:text-green-400">{generateResult.ats_score_after || generateResult.match_score || 0}</span>
              <span className="text-xs font-semibold text-green-600 dark:text-green-500">After</span>
            </div>
          </div>
          <p className="text-xs text-neutral-500 mt-2 max-w-[200px]">
            We rewrote your bullets to better match this specific job description.
          </p>
        </div>

        {/* Keywords Analysis */}
        <div className="md:col-span-2 space-y-4 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-xl p-6 shadow-sm">
          <h3 className="text-lg font-bold flex items-center gap-2"><CheckCircle2 className="w-5 h-5 text-green-500"/> Keyword Coverage</h3>
          
          <div className="space-y-4">
            {generateResult.keywords_added?.length > 0 && (
              <div>
                <p className="text-xs font-bold text-neutral-500 mb-2 uppercase">Keywords Added by AI</p>
                <div className="flex flex-wrap gap-2">
                  {generateResult.keywords_added.map((kw: string, i: number) => (
                    <span key={i} className="px-2.5 py-1 rounded-md text-xs font-mono font-medium border bg-green-50 border-green-200 text-green-700 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800/50">
                      + {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            {generateResult.keywords_missing?.length > 0 && (
              <div>
                <p className="text-xs font-bold text-neutral-500 mb-2 uppercase flex items-center gap-1"><AlertTriangle className="w-3 h-3"/> Still Missing (Consider Adding)</p>
                <div className="flex flex-wrap gap-2">
                  {generateResult.keywords_missing.map((kw: string, i: number) => (
                    <span key={i} className="px-2.5 py-1 rounded-md text-xs font-mono font-medium border bg-red-50 border-red-200 text-red-700 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800/50">
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-xl p-6 shadow-sm">
          <h3 className="text-lg font-bold mb-4">Actionable Recommendations</h3>
          {generateResult.recommendations?.length > 0 ? (
            <ol className="list-decimal pl-5 text-sm space-y-2 text-neutral-700 dark:text-neutral-300 marker:text-indigo-500 marker:font-bold">
              {generateResult.recommendations.map((rec: string, i: number) => (
                <li key={i} className="pl-1">{rec}</li>
              ))}
            </ol>
          ) : (
            <p className="text-sm text-neutral-500">Your resume looks incredibly strong for this role.</p>
          )}
        </div>

        {generateResult.sections_to_emphasize?.length > 0 && (
          <div className="bg-indigo-50 dark:bg-indigo-900/10 border border-indigo-100 dark:border-indigo-900/30 rounded-xl p-6 shadow-sm">
            <h3 className="text-lg font-bold mb-4 text-indigo-900 dark:text-indigo-300">Sections to Emphasize</h3>
            <ul className="list-disc pl-5 text-sm space-y-2 text-indigo-800 dark:text-indigo-400 marker:text-indigo-400">
              {generateResult.sections_to_emphasize.map((sec: string, i: number) => (
                <li key={i}>{sec}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="flex justify-end pt-8">
        <button 
          onClick={onNext} 
          className="px-8 py-3 rounded-xl font-bold text-white bg-black hover:bg-neutral-800 dark:bg-white dark:text-black dark:hover:bg-neutral-200 transition-all shadow-lg"
        >
          Review Optimized Resume →
        </button>
      </div>
    </div>
  );
};

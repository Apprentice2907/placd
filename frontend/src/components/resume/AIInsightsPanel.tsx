import React from 'react';
import type { ResumeProfile, KeywordTag, AnalysisPhase } from '../../types/resume';
import { TrendingUp, AlertCircle, ArrowRight } from 'lucide-react';

interface AIInsightsPanelProps {
  generateResult: any | null;
  isGenerating: boolean;
  analysisPhase: AnalysisPhase;
  keywords: KeywordTag[];
  analysisError: string | null;
  profile: ResumeProfile;
  onNext: () => void;
}

function AnalyzingProgress() {
  return (
    <div className="max-w-xl mx-auto py-16 flex flex-col items-center gap-6">
      {/* Spinner */}
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 rounded-full border-4 border-violet-100" />
        <div className="absolute inset-0 rounded-full border-4 border-violet-600 border-t-transparent animate-spin" />
      </div>

      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-800 mb-1">Tailoring your resume to the job...</h3>
        <p className="text-sm text-gray-500">This usually takes about 10 seconds.</p>
      </div>
    </div>
  );
}

export const AIInsightsPanel: React.FC<AIInsightsPanelProps> = ({
  generateResult, isGenerating, analysisPhase, keywords, analysisError, onNext
}) => {
  // Error
  if (analysisError) {
    return (
      <div className="max-w-xl mx-auto py-16 flex flex-col items-center gap-4 text-center">
        <div className="w-14 h-14 rounded-full bg-red-50 border border-red-200 flex items-center justify-center">
          <AlertCircle className="w-7 h-7 text-red-500" />
        </div>
        <h3 className="text-lg font-semibold text-gray-800">Analysis Failed</h3>
        <p className="text-sm text-gray-500 max-w-sm">{analysisError}</p>
        <p className="text-xs text-gray-400">Make sure VITE_GEMINI_API_KEY is set and try again.</p>
      </div>
    );
  }

  // Loading
  if (isGenerating || analysisPhase) {
    return <AnalyzingProgress />;
  }

  if (!generateResult) return null;

  const scoreBefore = generateResult.ats_score_before || 0;
  const scoreAfter  = generateResult.ats_score_after  || generateResult.match_score || 0;
  const improvement = scoreAfter - scoreBefore;

  return (
    <div className="max-w-4xl mx-auto space-y-5 animate-in fade-in pb-10">

      {/* Header */}
      <div className="pb-4 border-b border-gray-200">
        <h2 className="text-xl font-bold text-gray-900">AI Analysis Complete</h2>
        <p className="text-sm text-gray-500 mt-0.5">Your resume was critiqued and refined through 3 AI rounds.</p>
      </div>

      {/* Score + Recommendations */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Score card */}
        <div className="p-5 rounded-xl border border-gray-200 bg-white shadow-sm flex flex-col items-center justify-center text-center gap-3">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">ATS Score</p>
          <div className="flex items-center gap-4">
            <div className="text-center">
              <div className="text-3xl font-black text-gray-300">{scoreBefore}</div>
              <div className="text-[10px] text-gray-400 mt-0.5">Before</div>
            </div>
            <TrendingUp className="w-5 h-5 text-violet-500" />
            <div className="text-center">
              <div className="text-4xl font-black text-violet-600">{scoreAfter}</div>
              <div className="text-[10px] text-violet-500 mt-0.5">After</div>
            </div>
          </div>
          {improvement > 0 && (
            <span className="text-xs font-semibold text-green-700 bg-green-50 border border-green-200 px-2.5 py-0.5 rounded-full">
              +{improvement} pts
            </span>
          )}
        </div>

        {/* Recommendations */}
        <div className="md:col-span-2 p-5 rounded-xl border border-gray-200 bg-white shadow-sm">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Recommendations</h3>
          {generateResult.recommendations?.length > 0 ? (
            <ol className="space-y-2">
              {generateResult.recommendations.map((rec: string, i: number) => (
                <li key={i} className="flex gap-2 text-sm text-gray-600">
                  <span className="text-violet-500 font-bold flex-shrink-0">{i + 1}.</span>
                  {rec}
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-sm text-gray-400">Resume looks strong for this role — no major recommendations.</p>
          )}
        </div>
      </div>

      {/* AI Keyword Additions */}
      {(generateResult.keywords_added?.length > 0 || generateResult.keywords_missing?.length > 0) && (
        <div className="p-5 rounded-xl border border-gray-200 bg-white shadow-sm space-y-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Keyword Coverage</h3>
          {generateResult.keywords_added?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-green-600 mb-2">Added by AI</p>
              <div className="flex flex-wrap gap-2">
                {generateResult.keywords_added.map((kw: string, i: number) => (
                  <span key={i} className="px-2.5 py-1 rounded-md text-xs font-medium bg-green-50 border border-green-200 text-green-700">
                    + {kw}
                  </span>
                ))}
              </div>
            </div>
          )}
          {generateResult.keywords_missing?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-red-500 mb-2">Still Missing</p>
              <div className="flex flex-wrap gap-2">
                {generateResult.keywords_missing.map((kw: string, i: number) => (
                  <span key={i} className="px-2.5 py-1 rounded-md text-xs font-medium bg-red-50 border border-red-200 text-red-600">
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ATS Keyword Audit */}
      {keywords.length > 0 && (
        <div className="p-5 rounded-xl border border-gray-200 bg-white shadow-sm space-y-3">
          <div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">ATS Keyword Audit</h3>
            <p className="text-xs text-gray-400 mt-0.5">Top 15 keywords from the job description.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {keywords.map((kw, i) => (
              <span
                key={i}
                className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                  kw.status === 'PRESENT'
                    ? 'bg-green-50 border-green-200 text-green-700'
                    : 'bg-red-50 border-red-200 text-red-600'
                }`}
              >
                {kw.status === 'PRESENT' ? '✓' : '✗'} {kw.keyword}
              </span>
            ))}
          </div>
          <div className="flex gap-4 text-xs text-gray-400 pt-1">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
              {keywords.filter(k => k.status === 'PRESENT').length} present
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-red-400 inline-block" />
              {keywords.filter(k => k.status === 'MISSING').length} missing
            </span>
          </div>
        </div>
      )}

      {/* CTA */}
      <div className="flex justify-end pt-2">
        <button
          onClick={onNext}
          className="flex items-center gap-2 px-8 py-2.5 rounded-xl font-semibold text-sm text-white bg-violet-600 hover:bg-violet-700 transition-colors shadow-sm"
        >
          Review Optimized Resume
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

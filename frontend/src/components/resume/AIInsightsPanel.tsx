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

const phases: { key: AnalysisPhase; label: string; description: string }[] = [
  { key: 'generating', label: 'Generating Draft', description: 'Writing a tailored resume from your profile...' },
  { key: 'critiquing', label: 'Critiquing Resume', description: 'Senior hiring manager reviewing for weaknesses...' },
  { key: 'refining',   label: 'Refining Final Version', description: 'Fixing every issue raised in the critique...' },
  { key: 'keywords',  label: 'Extracting Keywords', description: 'Analyzing ATS keyword coverage...' },
];

function PhaseProgress({ currentPhase }: { currentPhase: AnalysisPhase }) {
  const currentIndex = phases.findIndex(p => p.key === currentPhase);
  const activePhase = phases[currentIndex];

  return (
    <div className="max-w-xl mx-auto py-20 flex flex-col items-center gap-8">
      {/* Animated glow orb */}
      <div className="relative w-20 h-20">
        <div className="absolute inset-0 rounded-full bg-purple-500/20 animate-ping" style={{ animationDuration: '1.5s' }} />
        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-purple-500/40 to-purple-700/20 animate-pulse" />
        <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center">
          <svg className="w-8 h-8 text-white animate-spin" style={{ animationDuration: '2s' }} fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
      </div>

      {/* Active phase info */}
      <div className="text-center">
        <h3 className="text-xl font-semibold text-white mb-1">{activePhase?.label}</h3>
        <p className="text-sm text-white/40">{activePhase?.description}</p>
      </div>

      {/* Phase steps */}
      <div className="w-full space-y-3">
        {phases.map((phase, i) => {
          const isDone = currentIndex > i;
          const isCurrent = currentIndex === i;
          return (
            <div
              key={phase.key}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-500 ${
                isDone
                  ? 'border-purple-500/30 bg-purple-500/10'
                  : isCurrent
                  ? 'border-purple-500/50 bg-purple-500/15 shadow-[0_0_16px_rgba(168,85,247,0.15)]'
                  : 'border-white/5 bg-white/[0.02]'
              }`}
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 transition-all duration-300 ${
                isDone
                  ? 'bg-purple-500 text-white'
                  : isCurrent
                  ? 'border-2 border-purple-400 text-purple-400'
                  : 'border border-white/15 text-white/20'
              }`}>
                {isDone ? '✓' : i + 1}
              </div>
              <span className={`text-sm font-medium transition-colors ${
                isDone ? 'text-purple-300' : isCurrent ? 'text-white' : 'text-white/25'
              }`}>
                {phase.label}
              </span>
              {isCurrent && (
                <div className="ml-auto flex gap-1">
                  {[0, 1, 2].map(d => (
                    <div
                      key={d}
                      className="w-1 h-1 rounded-full bg-purple-400 animate-bounce"
                      style={{ animationDelay: `${d * 0.15}s` }}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-xs text-white/20 text-center">This usually takes 20–40 seconds</p>
    </div>
  );
}

export const AIInsightsPanel: React.FC<AIInsightsPanelProps> = ({
  generateResult, isGenerating, analysisPhase, keywords, analysisError, onNext
}) => {
  // Error state
  if (analysisError) {
    return (
      <div className="max-w-xl mx-auto py-20 flex flex-col items-center gap-4 text-center">
        <div className="w-14 h-14 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center">
          <AlertCircle className="w-7 h-7 text-red-400" />
        </div>
        <h3 className="text-lg font-semibold text-white">Analysis Failed</h3>
        <p className="text-sm text-white/40 max-w-sm">{analysisError}</p>
        <p className="text-xs text-white/25">Make sure your Gemini API key is set in the frontend .env file.</p>
      </div>
    );
  }

  // Loading state
  if (isGenerating || analysisPhase) {
    return <PhaseProgress currentPhase={analysisPhase} />;
  }

  // No result yet
  if (!generateResult) return null;

  const scoreBefore = generateResult.ats_score_before || 0;
  const scoreAfter = generateResult.ats_score_after || generateResult.match_score || 0;
  const improvement = scoreAfter - scoreBefore;

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in pb-10">

      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-white/10">
        <div>
          <h2 className="text-xl font-bold text-white">AI Analysis Complete</h2>
          <p className="text-sm text-white/40 mt-0.5">Your resume has been critiqued and refined through 3 rounds of AI</p>
        </div>
      </div>

      {/* Score cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Score */}
        <div className="p-5 rounded-xl border border-white/10 bg-white/[0.03] flex flex-col items-center justify-center text-center gap-3">
          <p className="text-xs font-semibold text-white/30 uppercase tracking-wider">ATS Score</p>
          <div className="flex items-center gap-4">
            <div className="text-center">
              <div className="text-3xl font-black text-white/30">{scoreBefore}</div>
              <div className="text-[10px] text-white/25 mt-0.5">Before</div>
            </div>
            <TrendingUp className="w-6 h-6 text-purple-400" />
            <div className="text-center">
              <div className="text-4xl font-black text-purple-400">{scoreAfter}</div>
              <div className="text-[10px] text-purple-400/70 mt-0.5">After</div>
            </div>
          </div>
          {improvement > 0 && (
            <span className="text-xs font-semibold text-green-400 bg-green-400/10 border border-green-400/20 px-2 py-0.5 rounded-full">
              +{improvement} pts improvement
            </span>
          )}
        </div>

        {/* Recommendations */}
        <div className="md:col-span-2 p-5 rounded-xl border border-white/10 bg-white/[0.03]">
          <h3 className="text-sm font-bold text-white/80 mb-3 uppercase tracking-wider">Actionable Recommendations</h3>
          {generateResult.recommendations?.length > 0 ? (
            <ol className="space-y-2">
              {generateResult.recommendations.map((rec: string, i: number) => (
                <li key={i} className="flex gap-2 text-sm text-white/60">
                  <span className="text-purple-400 font-bold flex-shrink-0">{i + 1}.</span>
                  {rec}
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-sm text-white/30">No additional recommendations — your resume looks strong for this role.</p>
          )}
        </div>
      </div>

      {/* Keywords from AI */}
      {(generateResult.keywords_added?.length > 0 || generateResult.keywords_missing?.length > 0) && (
        <div className="p-5 rounded-xl border border-white/10 bg-white/[0.03] space-y-4">
          <h3 className="text-sm font-bold text-white/80 uppercase tracking-wider">Keyword Coverage (AI Tailoring)</h3>
          {generateResult.keywords_added?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-green-400/70 uppercase tracking-wider mb-2">Added by AI</p>
              <div className="flex flex-wrap gap-2">
                {generateResult.keywords_added.map((kw: string, i: number) => (
                  <span key={i} className="px-2.5 py-1 rounded-md text-xs font-medium bg-green-400/10 border border-green-400/25 text-green-400">
                    + {kw}
                  </span>
                ))}
              </div>
            </div>
          )}
          {generateResult.keywords_missing?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-red-400/70 uppercase tracking-wider mb-2">Still Missing</p>
              <div className="flex flex-wrap gap-2">
                {generateResult.keywords_missing.map((kw: string, i: number) => (
                  <span key={i} className="px-2.5 py-1 rounded-md text-xs font-medium bg-red-400/10 border border-red-400/25 text-red-400">
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ATS Keyword Tags from extraction round */}
      {keywords.length > 0 && (
        <div className="p-5 rounded-xl border border-white/10 bg-white/[0.03] space-y-3">
          <div>
            <h3 className="text-sm font-bold text-white/80 uppercase tracking-wider">ATS Keyword Audit</h3>
            <p className="text-xs text-white/30 mt-0.5">Top 15 keywords from the job description — green means present in your resume, red means missing.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {keywords.map((kw, i) => (
              <span
                key={i}
                className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
                  kw.status === 'PRESENT'
                    ? 'bg-green-400/10 border-green-400/30 text-green-400'
                    : 'bg-red-400/10 border-red-400/30 text-red-400'
                }`}
              >
                {kw.status === 'PRESENT' ? '✓' : '✗'} {kw.keyword}
              </span>
            ))}
          </div>
          <div className="flex gap-4 text-xs text-white/30 pt-1">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
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
          className="flex items-center gap-2 px-8 py-3 rounded-xl font-semibold text-sm text-white bg-purple-600 hover:bg-purple-500 transition-all duration-200 shadow-[0_0_20px_rgba(168,85,247,0.3)] hover:shadow-[0_0_28px_rgba(168,85,247,0.45)]"
        >
          Review Optimized Resume
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

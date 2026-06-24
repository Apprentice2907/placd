import React from 'react';
import { useResumeProfile } from '../hooks/useResumeProfile';
import { useResumeBuilder } from '../hooks/useResumeBuilder';

import { StepIndicator } from '../components/resume/StepIndicator';
import { ProfileForm } from '../components/resume/ProfileForm';
import { JobTargetForm } from '../components/resume/JobTargetForm';
import { AIInsightsPanel } from '../components/resume/AIInsightsPanel';
import { ResumePreview } from '../components/resume/ResumePreview';
import { OverflowWarning } from '../components/resume/OverflowWarning';
import { ResumeHistory } from '../components/resume/ResumeHistory';

import '../styles/resume-print.css';

export const ResumeBuilderPage: React.FC = () => {
  const sessionId = localStorage.getItem('placd-session-id') || '';

  const { profile, setProfile, loading } = useResumeProfile(sessionId);
  const builder = useResumeBuilder();

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="w-full min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-purple-500 border-t-transparent animate-spin" />
          <p className="text-sm text-white/40">Loading your profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-[#0a0a0a] min-h-screen pb-20 pt-6" style={{ color: '#fff' }}>
      <div className="max-w-5xl mx-auto px-4">

        {/* Header */}
        <div className="no-print mb-8 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-purple-500/30 bg-purple-500/10 text-purple-400 text-xs font-semibold mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
            AI-Powered • 3-Round Critic Loop
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Resume Builder
          </h1>
          <p className="text-white/40 mt-2 text-sm">
            Tailor your resume for any job with multi-round AI critique and refinement.
          </p>
        </div>

        {/* Step Indicator */}
        <StepIndicator currentStep={builder.currentStep} />

        {/* Step 1: Profile */}
        {builder.currentStep === 1 && (
          <ProfileForm
            profile={profile}
            onChange={setProfile}
            onNext={() => builder.setCurrentStep(2)}
          />
        )}

        {/* Step 2: Job Target */}
        {builder.currentStep === 2 && (
          <>
            <JobTargetForm
              jdText={builder.jdText}
              setJdText={builder.setJdText}
              company={builder.company}
              setCompany={builder.setCompany}
              role={builder.role}
              setRole={builder.setRole}
              onAnalyze={() => builder.startAnalysis(profile)}
            />
            <ResumeHistory />
          </>
        )}

        {/* Step 3: AI Analysis */}
        {builder.currentStep === 3 && (
          <AIInsightsPanel
            generateResult={builder.generateResult}
            isGenerating={builder.isGenerating}
            analysisPhase={builder.analysisPhase}
            keywords={builder.keywords}
            analysisError={builder.analysisError}
            profile={profile}
            onNext={() => builder.setCurrentStep(4)}
          />
        )}

        {/* Step 4: Preview */}
        {builder.currentStep === 4 && builder.generateResult && (
          <div className="animate-in fade-in">
            <OverflowWarning />
            <ResumePreview
              profile={profile}
              rewrite={builder.generateResult}
              bulletSelections={builder.bulletSelections}
              onToggleBullet={builder.toggleBullet}
              onExport={handlePrint}
            />
            <div className="mt-6 flex justify-center no-print">
              <button
                onClick={() => builder.setCurrentStep(3)}
                className="text-xs text-white/30 hover:text-white/50 transition-colors"
              >
                ← Back to AI Insights
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

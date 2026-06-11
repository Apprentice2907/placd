import React from 'react';
import { useResumeProfile } from '../hooks/useResumeProfile';
import { useResumeBuilder } from '../hooks/useResumeBuilder';

import { StepIndicator } from '../components/resume/StepIndicator';
import { ProfileForm } from '../components/resume/ProfileForm';
import { JobTargetForm } from '../components/resume/JobTargetForm';
import { AIInsightsPanel } from '../components/resume/AIInsightsPanel';
import { ResumePreview } from '../components/resume/ResumePreview';
import { OverflowWarning } from '../components/resume/OverflowWarning';

import '../styles/resume-print.css';

export const ResumeBuilderPage: React.FC = () => {
  const sessionId = localStorage.getItem('placd-session-id') || '';
  
  const { profile, setProfile, loading } = useResumeProfile(sessionId);
  const builder = useResumeBuilder();

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return <div className="p-10 text-center animate-pulse font-medium text-neutral-500">Loading your profile...</div>;
  }

  return (
    <div className="w-full bg-[var(--bg-background)] min-h-screen pb-20 pt-4">
      <div className="max-w-6xl mx-auto px-4">
        <div className="no-print mb-6 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">AI Resume Builder</h1>
          <p className="text-[var(--text-secondary)] mt-1">Tailor your resume instantly for any job using AI.</p>
        </div>

        <StepIndicator currentStep={builder.currentStep} />

        {builder.currentStep === 1 && (
          <ProfileForm 
            profile={profile} 
            onChange={setProfile} 
            onNext={() => builder.setCurrentStep(2)} 
          />
        )}

        {builder.currentStep === 2 && (
          <JobTargetForm 
            jdText={builder.jdText}
            setJdText={builder.setJdText}
            company={builder.company}
            setCompany={builder.setCompany}
            role={builder.role}
            setRole={builder.setRole}
            onAnalyze={() => builder.startAnalysis(profile)}
          />
        )}

        {builder.currentStep === 3 && (
          <AIInsightsPanel 
            research={builder.researchResult}
            rewrite={builder.rewriteResult}
            isRewriting={builder.isRewriting}
            profile={profile}
            onNext={() => builder.setCurrentStep(4)}
          />
        )}

        {builder.currentStep === 4 && builder.rewriteResult && (
          <div className="animate-in fade-in">
            <OverflowWarning />
            <ResumePreview 
              profile={profile}
              rewrite={builder.rewriteResult}
              bulletSelections={builder.bulletSelections}
              onToggleBullet={builder.toggleBullet}
              onExport={handlePrint}
            />
            <div className="mt-8 flex justify-center no-print">
               <button onClick={() => builder.setCurrentStep(3)} className="text-sm font-medium text-neutral-500 hover:text-black dark:hover:text-white transition-colors">← Back to AI Insights</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

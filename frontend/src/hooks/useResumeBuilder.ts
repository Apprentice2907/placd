import { useState, useCallback } from 'react';
import { api } from '../lib/api';
import type { ResearchResult, RewriteResult, ResumeProfile } from '../types/resume';

export function useResumeBuilder() {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1);
  const [jdText, setJdText] = useState('');
  const [company, setCompany] = useState('');
  const [role, setRole] = useState('');
  
  const [researchResult, setResearchResult] = useState<ResearchResult | null>(null);
  const [rewriteResult, setRewriteResult] = useState<RewriteResult | null>(null);
  
  const [isResearching, setIsResearching] = useState(false);
  const [isRewriting, setIsRewriting] = useState(false);
  
  const [bulletSelections, setBulletSelections] = useState<Record<string, 'original' | 'ai'>>({});

  const startAnalysis = useCallback(async (profile: ResumeProfile) => {
    setCurrentStep(3);
    setIsResearching(true);
    setIsRewriting(true);
    setResearchResult(null);
    setRewriteResult(null);
    
    let research: ResearchResult | null = null;
    try {
      research = await api.resume.research({ company, role, jd_text: jdText });
      setResearchResult(research);
    } catch (e) {
      console.error(e);
      research = { top_keywords: [], culture_signals: [], emphasis_notes: "Could not fetch company insights.", example_strong_bullets: [] };
      setResearchResult(research);
    } finally {
      setIsResearching(false);
    }

    try {
      const rewrite = await api.resume.rewrite({ profile, research, jd_text: jdText });
      setRewriteResult(rewrite);
      
      const initialSelections: Record<string, 'original' | 'ai'> = {};
      const allIds = [
        ...(profile.experience || []).map(e => e.id),
        ...(profile.projects || []).map(p => p.id)
      ];
      const returnedIds = new Set(rewrite.rewritten_bullets?.map((b: any) => b.id) || []);
      
      allIds.forEach(id => {
        if (returnedIds.has(id)) {
          initialSelections[id] = 'ai';
        } else {
          initialSelections[id] = 'original';
        }
      });
      
      setBulletSelections(initialSelections);
    } catch (e) {
      console.error(e);
    } finally {
      setIsRewriting(false);
    }
  }, [company, role, jdText]);

  const toggleBullet = useCallback((id: string, version: 'original' | 'ai') => {
    setBulletSelections(prev => ({ ...prev, [id]: version }));
  }, []);

  return {
    currentStep, setCurrentStep,
    jdText, setJdText,
    company, setCompany,
    role, setRole,
    researchResult, rewriteResult,
    isResearching, isRewriting,
    bulletSelections, toggleBullet,
    startAnalysis
  };
}

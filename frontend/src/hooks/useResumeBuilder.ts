import { useState, useCallback } from 'react';
import { api } from '../lib/api';
import type { ResumeProfile } from '../types/resume';

export function useResumeBuilder() {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1);
  const [jdText, setJdText] = useState('');
  const [company, setCompany] = useState('');
  const [role, setRole] = useState('');
  
  const [generateResult, setGenerateResult] = useState<any>(null);
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [bulletSelections, setBulletSelections] = useState<Record<string, 'original' | 'ai'>>({});

  const startAnalysis = useCallback(async (profile: ResumeProfile) => {
    setCurrentStep(3);
    setIsGenerating(true);
    setGenerateResult(null);
    
    try {
      const sessionId = localStorage.getItem('placd-session-id') || '';
      
      const payload = {
        session_id: sessionId,
        job_title: role,
        company_name: company,
        job_description: jdText,
        document_type: "resume"
      };

      const result = await api.resume.generate(payload);
      setGenerateResult(result);
      
      const initialSelections: Record<string, 'original' | 'ai'> = {};
      const allIds = [
        ...(profile.experience || []).map(e => e.id),
        ...(profile.projects || []).map(p => p.id)
      ];
      
      // Select AI by default since it returned tailored content
      allIds.forEach(id => {
        initialSelections[id] = 'ai';
      });
      
      setBulletSelections(initialSelections);
    } catch (e) {
      console.error(e);
    } finally {
      setIsGenerating(false);
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
    generateResult,
    isGenerating,
    bulletSelections, toggleBullet,
    startAnalysis
  };
}

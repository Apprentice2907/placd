import { useState, useCallback } from 'react';
import type { ResumeProfile, KeywordTag, AnalysisPhase } from '../types/resume';

const GEMINI_API_KEY = import.meta.env.VITE_GEMINI_API_KEY || '';
// gemini-2.0-flash: much higher free-tier RPM limits than 2.0
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`;

async function callGeminiJSON<T>(systemInstruction: string, userMessage: string): Promise<T> {
  const res = await fetch(GEMINI_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      system_instruction: { parts: [{ text: systemInstruction }] },
      contents: [{ role: 'user', parts: [{ text: userMessage }] }],
      generationConfig: { temperature: 0.3, maxOutputTokens: 2048, responseMimeType: 'application/json' },
    }),
  });
  if (!res.ok) throw new Error(`Gemini error ${res.status}: ${await res.text()}`);
  const text = (await res.json())?.candidates?.[0]?.content?.parts?.[0]?.text || '{}';
  
  const clean = text
    .replace(/^```json\s*/i, '')
    .replace(/^```\s*/i, '')
    .replace(/```\s*$/i, '')
    .trim();

  try {
    return JSON.parse(clean) as T;
  } catch {
    console.error('Gemini JSON parse failed:', text);
    return {} as T;
  }
}

export function useResumeBuilder() {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1);
  const [jdText, setJdText] = useState('');
  const [company, setCompany] = useState('');
  const [role, setRole] = useState('');

  const [generateResult, setGenerateResult] = useState<any>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [analysisPhase, setAnalysisPhase] = useState<AnalysisPhase>(null);
  const [keywords, setKeywords] = useState<KeywordTag[]>([]);
  const [bulletSelections, setBulletSelections] = useState<Record<string, 'original' | 'ai'>>({});
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const startAnalysis = useCallback(async (profile: ResumeProfile) => {
    setCurrentStep(3);
    setIsGenerating(true);
    setGenerateResult(null);
    setKeywords([]);
    setAnalysisError(null);

    // Compact profile — omit raw_resume_text to save tokens
    const profileSummary = JSON.stringify({
      personal: profile.personal,
      experience: profile.experience.map(e => ({
        id: e.id, company: e.company, role: e.role,
        start: e.start, end: e.end, bullets: e.bullets,
      })),
      projects: profile.projects.map(p => ({
        id: p.id, name: p.name, stack: p.stack, bullets: p.bullets,
      })),
      skills: profile.skills,
      education: profile.education.map(e => ({
        id: e.id, institution: e.institution, degree: e.degree,
        field: e.field, graduation_year: e.graduation_year,
      })),
    });

    // Truncate JD to 800 chars to save input tokens
    const jdShort = jdText.length > 800 ? jdText.slice(0, 800) + '...' : jdText;

    try {
      setAnalysisPhase('analyzing');
      console.log('[Resume AI] Tailoring resume...');

      const systemPrompt = `You are an expert resume writer. Tailor the resume to the job description. Be concise, use strong action verbs, and optimize for ATS.
Output exactly this JSON shape:
{
  "summary": "string",
  "rewritten_bullets": { "role_or_project": ["bullet1"] },
  "skills_reordered": ["skill1"],
  "match_score": 85,
  "keywords": [{"keyword": "string", "status": "PRESENT"|"MISSING"}]
}`;

      const userPrompt = `PROFILE: ${profileSummary}\n\nROLE: ${role} at ${company}\n\nJD: ${jdShort}`;

      const finalResult = await callGeminiJSON<{
        summary: string;
        rewritten_bullets: Record<string, string[]>;
        skills_reordered: string[];
        match_score: number;
        keywords: KeywordTag[];
      }>(systemPrompt, userPrompt);

      console.log('[Resume AI] Analysis done', finalResult);

      const rewrittenBulletsArray = Object.entries(finalResult.rewritten_bullets || {}).map(
        ([id, bullets]) => ({ id, bullets })
      );

      const safeResult = {
        summary: finalResult.summary || '',
        rewritten_bullets: rewrittenBulletsArray,
        skills_reordered: finalResult.skills_reordered || [],
        match_score: finalResult.match_score || 0,
        ats_score_before: 0,
        ats_score_after: finalResult.match_score || 0,
        keywords_added: [],
        keywords_missing: [],
        recommendations: [],
        sections_to_emphasize: [],
        placeholders: [],
        missing_keywords: [],
      };
      setGenerateResult(safeResult);

      const validKws = Array.isArray(finalResult.keywords)
        ? finalResult.keywords.filter((k: any) => k.keyword && (k.status === 'PRESENT' || k.status === 'MISSING'))
        : [];
      setKeywords(validKws);

      // Default all bullets to AI version
      const initialSelections: Record<string, 'original' | 'ai'> = {};
      [...(profile.experience || []).map(e => e.id), ...(profile.projects || []).map(p => p.id)]
        .forEach(id => { initialSelections[id] = 'ai'; });
      setBulletSelections(initialSelections);

    } catch (e: any) {
      console.error('[Resume AI] Failed:', e);
      setAnalysisError(e?.message || 'AI analysis failed. Check your API key and try again.');
    } finally {
      setIsGenerating(false);
      setAnalysisPhase(null);
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
    analysisPhase,
    keywords,
    analysisError,
    bulletSelections, toggleBullet,
    startAnalysis,
  };
}

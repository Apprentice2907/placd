import { useState, useCallback } from 'react';
import type { ResumeProfile, KeywordTag, AnalysisPhase } from '../types/resume';

const GEMINI_API_KEY = import.meta.env.VITE_GEMINI_API_KEY || '';
// gemini-1.5-flash: much higher free-tier RPM limits than 2.0
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`;

const delay = (ms: number) => new Promise(r => setTimeout(r, ms));

async function callGemini(systemInstruction: string, userMessage: string): Promise<string> {
  const res = await fetch(GEMINI_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      system_instruction: { parts: [{ text: systemInstruction }] },
      contents: [{ role: 'user', parts: [{ text: userMessage }] }],
      generationConfig: { temperature: 0.7, maxOutputTokens: 1024 },
    }),
  });
  if (!res.ok) throw new Error(`Gemini error ${res.status}: ${await res.text()}`);
  return (await res.json())?.candidates?.[0]?.content?.parts?.[0]?.text || '';
}

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
  try {
    return JSON.parse(text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim()) as T;
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
      // ── Round 1: Generator ──────────────────────────────────────────────
      setAnalysisPhase('generating');
      console.log('[Resume AI] Round 1: Generating...');

      const round1Result = await callGeminiJSON<{
        summary: string;
        rewritten_bullets: { id: string; bullets: string[] }[];
        skills_reordered: string[];
        match_score: number;
      }>(
        // System (~40 words)
        `Expert resume writer. Output ATS-optimized resume as JSON: {summary, rewritten_bullets:[{id,bullets}], skills_reordered, match_score}. Max 400 words total. Use exact IDs from profile.`,
        // User prompt
        `PROFILE: ${profileSummary}\n\nROLE: ${role} at ${company}\n\nJD: ${jdShort}\n\nReturn JSON only.`
      );
      console.log('[Resume AI] Round 1 done');

      await delay(2000);

      // ── Round 2: Critic ─────────────────────────────────────────────────
      setAnalysisPhase('critiquing');
      console.log('[Resume AI] Round 2: Critiquing...');

      const round2Critique = await callGemini(
        // System (~35 words)
        `Senior hiring manager, 95% rejection rate. List every resume flaw: weak verbs, missing metrics, vague bullets, missing ATS keywords. Be blunt. Numbered list only.`,
        `JD: ${jdShort}\n\nRESUME: ${JSON.stringify(round1Result)}\n\nList flaws:`
      );
      console.log('[Resume AI] Round 2 done');

      await delay(2000);

      // ── Round 3: Refiner ────────────────────────────────────────────────
      setAnalysisPhase('refining');
      console.log('[Resume AI] Round 3: Refining...');

      const finalResult = await callGeminiJSON<{
        summary: string;
        rewritten_bullets: { id: string; bullets: string[] }[];
        skills_reordered: string[];
        match_score: number;
        ats_score_before: number;
        ats_score_after: number;
        keywords_added: string[];
        keywords_missing: string[];
        recommendations: string[];
        sections_to_emphasize: string[];
      }>(
        // System (~35 words)
        `Expert resume writer. Fix all critique issues. Output JSON: {summary, rewritten_bullets:[{id,bullets}], skills_reordered, match_score, ats_score_before, ats_score_after, keywords_added, keywords_missing, recommendations, sections_to_emphasize}.`,
        `DRAFT: ${JSON.stringify(round1Result)}\n\nCRITIQUE: ${round2Critique}\n\nJD: ${jdShort}\n\nReturn improved JSON:`
      );
      console.log('[Resume AI] Round 3 done');

      const safeResult = {
        summary: finalResult.summary || round1Result.summary || '',
        rewritten_bullets: finalResult.rewritten_bullets || round1Result.rewritten_bullets || [],
        skills_reordered: finalResult.skills_reordered || round1Result.skills_reordered || [],
        match_score: finalResult.match_score || round1Result.match_score || 0,
        ats_score_before: finalResult.ats_score_before || 0,
        ats_score_after: finalResult.ats_score_after || finalResult.match_score || 0,
        keywords_added: finalResult.keywords_added || [],
        keywords_missing: finalResult.keywords_missing || [],
        recommendations: finalResult.recommendations || [],
        sections_to_emphasize: finalResult.sections_to_emphasize || [],
        placeholders: [],
        missing_keywords: finalResult.keywords_missing || [],
      };
      setGenerateResult(safeResult);

      await delay(2000);

      // ── Round 4: Keyword Extraction ─────────────────────────────────────
      setAnalysisPhase('keywords');
      console.log('[Resume AI] Round 4: Keywords...');

      const kwResult = await callGeminiJSON<KeywordTag[]>(
        // System (~30 words)
        `ATS expert. Return JSON array of top 15 keywords from the JD, each marked PRESENT or MISSING in the resume: [{keyword,status}].`,
        `JD: ${jdShort}\n\nRESUME SUMMARY: ${safeResult.summary}\nSKILLS: ${safeResult.skills_reordered.join(', ')}\nKEYWORDS ADDED: ${safeResult.keywords_added.join(', ')}`
      );

      const validKws = Array.isArray(kwResult)
        ? kwResult.filter(k => k.keyword && (k.status === 'PRESENT' || k.status === 'MISSING'))
        : [];
      setKeywords(validKws);
      console.log('[Resume AI] Round 4 done:', validKws);

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

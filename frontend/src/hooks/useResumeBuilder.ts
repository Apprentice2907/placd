import { useState, useCallback } from 'react';
import type { ResumeProfile, KeywordTag, AnalysisPhase } from '../types/resume';

const GEMINI_API_KEY = import.meta.env.VITE_GEMINI_API_KEY || '';
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`;

async function callGemini(systemInstruction: string, userMessage: string): Promise<string> {
  const body = {
    system_instruction: {
      parts: [{ text: systemInstruction }]
    },
    contents: [
      { role: 'user', parts: [{ text: userMessage }] }
    ],
    generationConfig: {
      temperature: 0.7,
      maxOutputTokens: 4096,
    }
  };

  const res = await fetch(GEMINI_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Gemini API error ${res.status}: ${err}`);
  }

  const data = await res.json();
  return data?.candidates?.[0]?.content?.parts?.[0]?.text || '';
}

async function callGeminiJSON<T>(systemInstruction: string, userMessage: string): Promise<T> {
  const body = {
    system_instruction: {
      parts: [{ text: systemInstruction }]
    },
    contents: [
      { role: 'user', parts: [{ text: userMessage }] }
    ],
    generationConfig: {
      temperature: 0.3,
      maxOutputTokens: 4096,
      responseMimeType: 'application/json',
    }
  };

  const res = await fetch(GEMINI_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Gemini API error ${res.status}: ${err}`);
  }

  const data = await res.json();
  const text = data?.candidates?.[0]?.content?.parts?.[0]?.text || '{}';
  
  try {
    // Strip markdown code fences if present
    const cleaned = text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim();
    return JSON.parse(cleaned) as T;
  } catch {
    console.error('Failed to parse Gemini JSON response:', text);
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

    const profileSummary = JSON.stringify({
      personal: profile.personal,
      experience: profile.experience.map(e => ({
        id: e.id,
        company: e.company,
        role: e.role,
        start: e.start,
        end: e.end,
        bullets: e.bullets,
      })),
      projects: profile.projects.map(p => ({
        id: p.id,
        name: p.name,
        stack: p.stack,
        bullets: p.bullets,
      })),
      skills: profile.skills,
      education: profile.education,
      achievements: profile.achievements,
      ...(profile.raw_resume_text ? { raw_resume_text: profile.raw_resume_text } : {}),
    }, null, 2);

    try {
      // ── Round 1: Generator ──────────────────────────────────────────────
      setAnalysisPhase('generating');
      console.log('[Resume AI] Round 1: Generating draft...');

      const generatorSystem = `You are an expert resume writer. Create a strong, ATS-optimized resume tailored to the job description provided. 
Output the resume as a JSON object with this exact shape:
{
  "summary": "2-3 sentence professional summary",
  "rewritten_bullets": [
    { "id": "exp_1", "bullets": ["bullet 1", "bullet 2"] }
  ],
  "skills_reordered": ["skill1", "skill2"],
  "match_score": 82
}
Include ALL experience and project IDs from the profile. Reorder skills so JD-relevant skills come first.`;

      const generatorPrompt = `CANDIDATE PROFILE:
${profileSummary}

TARGET ROLE: ${role} at ${company}

JOB DESCRIPTION:
${jdText}

Generate a tailored resume JSON. Use the exact IDs from the profile for rewritten_bullets.`;

      const round1Result = await callGeminiJSON<{
        summary: string;
        rewritten_bullets: { id: string; bullets: string[] }[];
        skills_reordered: string[];
        match_score: number;
      }>(generatorSystem, generatorPrompt);

      console.log('[Resume AI] Round 1 complete:', round1Result);

      // ── Round 2: Critic ─────────────────────────────────────────────────
      setAnalysisPhase('critiquing');
      console.log('[Resume AI] Round 2: Critiquing...');

      const criticSystem = `You are a senior hiring manager at a top tech company who rejects 95% of resumes. Review this resume and list every single flaw bluntly — weak action verbs, missing metrics, vague bullets, ATS keywords missing from the job description, formatting issues, anything that would make you reject it immediately. Be harsh and specific. Output as plain text, numbered list.`;

      const criticPrompt = `JOB DESCRIPTION:
${jdText}

RESUME DRAFT:
${JSON.stringify(round1Result, null, 2)}

List every flaw. Be brutal. Number each issue.`;

      const round2Critique = await callGemini(criticSystem, criticPrompt);
      console.log('[Resume AI] Round 2 critique:', round2Critique);

      // ── Round 3: Refiner ────────────────────────────────────────────────
      setAnalysisPhase('refining');
      console.log('[Resume AI] Round 3: Refining...');

      const refinerSystem = `You are an expert resume writer. You have received harsh feedback on a resume draft. Revise the resume to fix every single issue raised in the critique. Make it exceptional.
Output JSON with this exact shape:
{
  "summary": "improved summary",
  "rewritten_bullets": [
    { "id": "exp_1", "bullets": ["improved bullet 1", "improved bullet 2"] }
  ],
  "skills_reordered": ["skill1", "skill2"],
  "match_score": 90,
  "ats_score_before": 60,
  "ats_score_after": 90,
  "keywords_added": ["keyword1"],
  "keywords_missing": ["keyword2"],
  "recommendations": ["tip1", "tip2"],
  "sections_to_emphasize": ["section1"]
}`;

      const refinerPrompt = `ORIGINAL RESUME DRAFT:
${JSON.stringify(round1Result, null, 2)}

CRITIC FEEDBACK:
${round2Critique}

JOB DESCRIPTION:
${jdText}

Fix all critiqued issues and output the improved resume JSON.`;

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
      }>(refinerSystem, refinerPrompt);

      console.log('[Resume AI] Round 3 final result:', finalResult);

      // Ensure required fields are present
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

      // ── Round 4: Keyword Extraction ─────────────────────────────────────
      setAnalysisPhase('keywords');
      console.log('[Resume AI] Round 4: Extracting keywords...');

      const keywordSystem = `You are an ATS expert. Extract the top 15 most important ATS keywords from a job description and check if each appears in a resume. Return ONLY a valid JSON array with no markdown: [{"keyword": "...", "status": "PRESENT"}, {"keyword": "...", "status": "MISSING"}]`;

      const keywordPrompt = `JOB DESCRIPTION:
${jdText}

FINAL RESUME:
${JSON.stringify(safeResult, null, 2)}

Extract top 15 ATS keywords. Mark each as PRESENT (found in resume) or MISSING (not in resume). Return JSON array only.`;

      const kwResult = await callGeminiJSON<KeywordTag[]>(keywordSystem, keywordPrompt);
      const validKws = Array.isArray(kwResult)
        ? kwResult.filter(k => k.keyword && (k.status === 'PRESENT' || k.status === 'MISSING'))
        : [];
      
      setKeywords(validKws);
      console.log('[Resume AI] Keywords:', validKws);

      // Set default bullet selections
      const initialSelections: Record<string, 'original' | 'ai'> = {};
      const allIds = [
        ...(profile.experience || []).map(e => e.id),
        ...(profile.projects || []).map(p => p.id)
      ];
      allIds.forEach(id => { initialSelections[id] = 'ai'; });
      setBulletSelections(initialSelections);

    } catch (e: any) {
      console.error('[Resume AI] Analysis failed:', e);
      setAnalysisError(e?.message || 'AI analysis failed. Please check your API key and try again.');
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
    startAnalysis
  };
}

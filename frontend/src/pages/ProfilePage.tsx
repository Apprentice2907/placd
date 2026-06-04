import React, { useState, useEffect, useRef } from 'react';
import { api } from '../lib/api';
import { Save, Plus, Trash2, CheckCircle2, User, FileText, Briefcase, Code, Award, GraduationCap, Check } from 'lucide-react';

const generateSessionId = () => {
  let sessionId = localStorage.getItem('placd-session-id');
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem('placd-session-id', sessionId);
  }
  return sessionId;
};

const SECTIONS = [
  { id: 'personal', label: 'Personal Info', icon: User },
  { id: 'summary', label: 'Professional Summary', icon: FileText },
  { id: 'experience', label: 'Work Experience', icon: Briefcase },
  { id: 'projects', label: 'Projects', icon: Code },
  { id: 'skills', label: 'Skills', icon: CheckCircle2 },
  { id: 'education', label: 'Education', icon: GraduationCap },
  { id: 'certifications', label: 'Certifications & Achievements', icon: Award },
];

export const ProfilePage: React.FC = () => {
  const sessionId = generateSessionId();
  
  const [profile, setProfile] = useState<any>({
    session_id: sessionId,
    full_name: '', email: '', phone: '', location: '', linkedin_url: '', github_url: '', portfolio_url: '',
    professional_summary: '',
    education: [], experiences: [], projects: [], skills: { languages: [], frameworks: [], tools: [], databases: [] },
    certifications: [], achievements: []
  });
  
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [activeSection, setActiveSection] = useState('personal');

  // Load Profile
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const data = await api.profile.get(sessionId);
        setProfile((prev: any) => ({ ...prev, ...data }));
      } catch (e) {
        // Try local storage draft
        const draft = localStorage.getItem('placd-profile-draft');
        if (draft) {
          try { setProfile(JSON.parse(draft)); } catch {}
        }
      } finally {
        setIsLoading(false);
      }
    };
    loadProfile();
  }, [sessionId]);

  // Debounced auto-save to local storage & API
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  useEffect(() => {
    if (isLoading) return;
    
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    
    debounceTimer.current = setTimeout(() => {
      localStorage.setItem('placd-profile-draft', JSON.stringify(profile));
      // Auto-save to backend silently
      api.profile.upsert(profile).catch(() => {});
      setSaveMessage('Saved locally');
      setTimeout(() => setSaveMessage(''), 2000);
    }, 1000);
    
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [profile, isLoading]);

  const handleManualSave = async () => {
    setIsSaving(true);
    try {
      await api.profile.upsert(profile);
      setSaveMessage('Profile saved successfully!');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (e) {
      setSaveMessage('Failed to save.');
    } finally {
      setIsSaving(false);
    }
  };

  const calculateProgress = () => {
    let score = 0;
    if (profile.full_name) score += 10;
    if (profile.email) score += 10;
    if (profile.professional_summary?.length > 20) score += 20;
    if (profile.experiences?.length > 0) score += 20;
    if (profile.projects?.length > 0) score += 20;
    if (Object.values(profile.skills || {}).some((arr: any) => arr.length > 0)) score += 20;
    return score;
  };

  const progress = calculateProgress();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setProfile((prev: any) => ({ ...prev, [name]: value }));
  };

  const updateArray = (key: string, index: number, field: string, value: any) => {
    const newArr = [...(profile[key] || [])];
    newArr[index] = { ...newArr[index], [field]: value };
    setProfile({ ...profile, [key]: newArr });
  };

  const updateArrayString = (key: string, index: number, value: string) => {
    const newArr = [...(profile[key] || [])];
    newArr[index] = value;
    setProfile({ ...profile, [key]: newArr });
  };

  const addArrayItem = (key: string, defaultItem: any) => {
    setProfile({ ...profile, [key]: [...(profile[key] || []), defaultItem] });
  };

  const removeArrayItem = (key: string, index: number) => {
    const newArr = [...(profile[key] || [])];
    newArr.splice(index, 1);
    setProfile({ ...profile, [key]: newArr });
  };

  const handleBulletsChange = (key: string, index: number, value: string) => {
    const bullets = value.split('\n').filter(b => b.trim() !== '');
    updateArray(key, index, 'bullets', bullets);
  };

  const handleTagsChange = (key: string, index: number, value: string) => {
    const tags = value.split(',').map(t => t.trim()).filter(t => t !== '');
    updateArray(key, index, 'tech_stack', tags);
  };

  const handleSkillsChange = (category: string, value: string) => {
    const skills = value.split(',').map(s => s.trim()).filter(s => s !== '');
    setProfile({ ...profile, skills: { ...profile.skills, [category]: skills } });
  };

  const scrollToSection = (id: string) => {
    setActiveSection(id);
    document.getElementById(`section-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  if (isLoading) return <div className="p-8 text-center h-[calc(100vh-80px)] flex items-center justify-center">Loading profile...</div>;

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 flex flex-col md:flex-row gap-8 relative items-start">
      
      {/* STICKY LEFT NAV */}
      <div className="w-full md:w-64 flex-shrink-0 sticky top-8 space-y-6 bg-white dark:bg-[#0a0a0f] border-r border-black/8 dark:border-white/8 p-4 rounded-xl">
        <div>
          <h1 className="text-2xl font-bold tracking-tight mb-1">My Profile</h1>
          <p className="text-sm text-[var(--text-secondary)]">The brain of your resume.</p>
        </div>
        
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs font-medium">
            <span>Profile Completeness</span>
            <span className={progress === 100 ? 'text-green-500' : 'text-indigo-500'}>{progress}%</span>
          </div>
          <div className="w-full h-2 bg-black/8 dark:bg-white/8 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 ${progress === 100 ? 'bg-green-500' : 'bg-indigo-500'}`} 
              style={{ width: `${progress}%` }} 
            />
          </div>
        </div>

        <nav className="hidden md:flex flex-col gap-1 border-l-2 border-[var(--border-color)] pl-4">
          {SECTIONS.map((sec) => (
            <button
              key={sec.id}
              onClick={() => scrollToSection(sec.id)}
              className={`flex items-center gap-3 py-2 text-sm font-medium transition-colors text-left
                ${activeSection === sec.id ? 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-medium' : 'text-black/60 dark:text-white/60 hover:bg-black/5 dark:hover:bg-white/5'}`}
            >
              <sec.icon className="w-4 h-4" />
              {sec.label}
            </button>
          ))}
        </nav>

        <button 
          onClick={handleManualSave}
          disabled={isSaving}
          className="w-full mt-4 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg px-4 py-2 transition-colors"
        >
          {isSaving ? 'Saving...' : <><Save className="w-4 h-4" /> Save Profile</>}
        </button>
        {saveMessage && (
          <p className="text-xs text-center font-medium text-green-600 dark:text-green-400 flex items-center justify-center gap-1">
            <Check className="w-3 h-3" /> {saveMessage}
          </p>
        )}
      </div>

      {/* SCROLLING MAIN CONTENT */}
      <div className="flex-1 space-y-16 pb-32 max-w-3xl">
        
        {/* 1. PERSONAL INFO */}
        <section id="section-personal" className="space-y-6 scroll-mt-8">
          <div className="border-b border-[var(--border-color)] pb-2">
            <h2 className="text-xs font-semibold tracking-widest uppercase text-black dark:text-white border-l-2 border-indigo-500 pl-3 flex items-center gap-2"><User className="w-5 h-5 text-indigo-500" /> Personal Information</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Full Name</label>
              <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" name="full_name" value={profile.full_name || ''} onChange={handleChange} />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Email</label>
              <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" name="email" value={profile.email || ''} onChange={handleChange} />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Phone</label>
              <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" name="phone" value={profile.phone || ''} onChange={handleChange} />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Location (City, State)</label>
              <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" name="location" value={profile.location || ''} onChange={handleChange} />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">LinkedIn URL</label>
              <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" name="linkedin_url" value={profile.linkedin_url || ''} onChange={handleChange} />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">GitHub URL</label>
              <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" name="github_url" value={profile.github_url || ''} onChange={handleChange} />
            </div>
            <div className="space-y-1 md:col-span-2">
              <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Portfolio / Website URL</label>
              <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" name="portfolio_url" value={profile.portfolio_url || ''} onChange={handleChange} />
            </div>
          </div>
        </section>

        {/* 2. SUMMARY */}
        <section id="section-summary" className="space-y-6 scroll-mt-8">
          <div className="border-b border-[var(--border-color)] pb-2 flex justify-between items-end">
            <h2 className="text-xs font-semibold tracking-widest uppercase text-black dark:text-white border-l-2 border-indigo-500 pl-3 flex items-center gap-2"><FileText className="w-5 h-5 text-indigo-500" /> Professional Summary</h2>
            <span className="text-xs text-[var(--text-secondary)]">{profile.professional_summary?.length || 0}/500 chars</span>
          </div>
          <textarea 
            className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30 min-h-[120px] resize-y" 
            name="professional_summary" 
            placeholder="A compelling overview of your career, top achievements, and primary focus areas..." 
            maxLength={500}
            value={profile.professional_summary || ''} 
            onChange={handleChange} 
          />
        </section>

        {/* 3. EXPERIENCE */}
        <section id="section-experience" className="space-y-6 scroll-mt-8">
          <div className="border-b border-[var(--border-color)] pb-2 flex justify-between items-center">
            <h2 className="text-xs font-semibold tracking-widest uppercase text-black dark:text-white border-l-2 border-indigo-500 pl-3 flex items-center gap-2"><Briefcase className="w-5 h-5 text-indigo-500" /> Work Experience</h2>
          </div>
          
          <div className="space-y-6">
            {(profile.experiences || []).map((exp: any, i: number) => (
              <div key={i} className="p-6 bg-[#f5f5f7] dark:bg-[#111118] border border-black/8 dark:border-white/8 rounded-xl space-y-4 relative group">
                <button onClick={() => removeArrayItem('experiences', i)} className="absolute top-5 right-5 text-black/30 hover:text-red-500 dark:text-white/30 dark:hover:text-red-400 transition-colors transition-colors"><Trash2 className="w-4 h-4"/></button>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pr-8">
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Job Title</label>
                    <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="e.g. Senior Software Engineer" value={exp.title || ''} onChange={(e) => updateArray('experiences', i, 'title', e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Company</label>
                    <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="e.g. Stripe" value={exp.company || ''} onChange={(e) => updateArray('experiences', i, 'company', e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Dates</label>
                    <div className="flex items-center gap-2">
                      <input className="w-1/2 bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="Jan 2020" value={exp.start || ''} onChange={(e) => updateArray('experiences', i, 'start', e.target.value)} />
                      <span className="text-[var(--text-secondary)]">-</span>
                      <input className="w-1/2 bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="Present" value={exp.end || ''} onChange={(e) => updateArray('experiences', i, 'end', e.target.value)} />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Location</label>
                    <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="e.g. San Francisco, CA" value={exp.location || ''} onChange={(e) => updateArray('experiences', i, 'location', e.target.value)} />
                  </div>
                </div>
                
                <div className="space-y-1 pt-2">
                  <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Bullet Points (One per line)</label>
                  <textarea 
                    className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30 min-h-[120px]" 
                    placeholder="• Developed X using Y resulting in Z..." 
                    value={(exp.bullets || []).join('\n')} 
                    onChange={(e) => handleBulletsChange('experiences', i, e.target.value)} 
                  />
                </div>
              </div>
            ))}
            
            <button 
              onClick={() => addArrayItem('experiences', { title: '', company: '', location: '', start: '', end: '', bullets: [] })} 
              className="w-full py-4 border border-dashed border-black/20 dark:border-white/20 rounded-xl text-black/60 dark:text-white/60 hover:border-indigo-500 hover:text-indigo-500 transition-colors flex items-center justify-center gap-2 text-sm font-medium"
            >
              <Plus className="w-4 h-4"/> Add Experience
            </button>
          </div>
        </section>

        {/* 4. PROJECTS */}
        <section id="section-projects" className="space-y-6 scroll-mt-8">
          <div className="border-b border-[var(--border-color)] pb-2 flex justify-between items-center">
            <h2 className="text-xs font-semibold tracking-widest uppercase text-black dark:text-white border-l-2 border-indigo-500 pl-3 flex items-center gap-2"><Code className="w-5 h-5 text-indigo-500" /> Projects</h2>
          </div>
          
          <div className="space-y-6">
            {(profile.projects || []).map((proj: any, i: number) => (
              <div key={i} className="p-6 bg-[#f5f5f7] dark:bg-[#111118] border border-black/8 dark:border-white/8 rounded-xl space-y-4 relative">
                <button onClick={() => removeArrayItem('projects', i)} className="absolute top-5 right-5 text-black/30 hover:text-red-500 dark:text-white/30 dark:hover:text-red-400 transition-colors transition-colors"><Trash2 className="w-4 h-4"/></button>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pr-8">
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Project Name</label>
                    <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="e.g. E-Commerce Platform" value={proj.name || ''} onChange={(e) => updateArray('projects', i, 'name', e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Tech Stack (comma separated)</label>
                    <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="React, Node.js, PostgreSQL" value={(proj.tech_stack || []).join(', ')} onChange={(e) => handleTagsChange('projects', i, e.target.value)} />
                  </div>
                  <div className="space-y-1 md:col-span-2">
                    <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">GitHub / Live URL</label>
                    <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="https://github.com/..." value={proj.github_url || ''} onChange={(e) => updateArray('projects', i, 'github_url', e.target.value)} />
                  </div>
                </div>
                
                <div className="space-y-1">
                  <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Description (Bullet 1)</label>
                  <textarea className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="What is it and how did you build it?" value={proj.description || ''} onChange={(e) => updateArray('projects', i, 'description', e.target.value)} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Impact (Bullet 2)</label>
                  <textarea className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="What was the result? Reduced latency by 50%..." value={proj.impact || ''} onChange={(e) => updateArray('projects', i, 'impact', e.target.value)} />
                </div>
              </div>
            ))}
            
            <button 
              onClick={() => addArrayItem('projects', { name: '', description: '', tech_stack: [], github_url: '', impact: '' })} 
              className="w-full py-4 border border-dashed border-black/20 dark:border-white/20 rounded-xl text-black/60 dark:text-white/60 hover:border-indigo-500 hover:text-indigo-500 transition-colors flex items-center justify-center gap-2 text-sm font-medium"
            >
              <Plus className="w-4 h-4"/> Add Project
            </button>
          </div>
        </section>

        {/* 5. SKILLS */}
        <section id="section-skills" className="space-y-6 scroll-mt-8">
          <div className="border-b border-[var(--border-color)] pb-2 flex justify-between items-center">
            <h2 className="text-xs font-semibold tracking-widest uppercase text-black dark:text-white border-l-2 border-indigo-500 pl-3 flex items-center gap-2"><CheckCircle2 className="w-5 h-5 text-indigo-500" /> Skills</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Languages</label>
              <textarea 
                className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30 min-h-[80px]" 
                placeholder="Python, JavaScript, Go..." 
                value={(profile.skills?.languages || []).join(', ')} 
                onChange={(e) => handleSkillsChange('languages', e.target.value)} 
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Frameworks</label>
              <textarea 
                className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30 min-h-[80px]" 
                placeholder="React, Django, FastAPI..." 
                value={(profile.skills?.frameworks || []).join(', ')} 
                onChange={(e) => handleSkillsChange('frameworks', e.target.value)} 
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Databases</label>
              <textarea 
                className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30 min-h-[80px]" 
                placeholder="PostgreSQL, MongoDB, Redis..." 
                value={(profile.skills?.databases || []).join(', ')} 
                onChange={(e) => handleSkillsChange('databases', e.target.value)} 
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Tools & DevOps</label>
              <textarea 
                className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30 min-h-[80px]" 
                placeholder="Docker, Git, AWS, CI/CD..." 
                value={(profile.skills?.tools || []).join(', ')} 
                onChange={(e) => handleSkillsChange('tools', e.target.value)} 
              />
            </div>
          </div>
        </section>
        
        {/* 6. EDUCATION */}
        <section id="section-education" className="space-y-6 scroll-mt-8">
          <div className="border-b border-[var(--border-color)] pb-2 flex justify-between items-center">
            <h2 className="text-xs font-semibold tracking-widest uppercase text-black dark:text-white border-l-2 border-indigo-500 pl-3 flex items-center gap-2"><GraduationCap className="w-5 h-5 text-indigo-500" /> Education</h2>
          </div>
          
          <div className="space-y-6">
            {(profile.education || []).map((edu: any, i: number) => (
              <div key={i} className="p-6 bg-[#f5f5f7] dark:bg-[#111118] border border-black/8 dark:border-white/8 rounded-xl space-y-4 relative">
                <button onClick={() => removeArrayItem('education', i)} className="absolute top-5 right-5 text-black/30 hover:text-red-500 dark:text-white/30 dark:hover:text-red-400 transition-colors transition-colors"><Trash2 className="w-4 h-4"/></button>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pr-8">
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Degree</label>
                    <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="B.S. Computer Science" value={edu.degree || ''} onChange={(e) => updateArray('education', i, 'degree', e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Institution</label>
                    <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="University of Tech" value={edu.institution || ''} onChange={(e) => updateArray('education', i, 'institution', e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">Dates</label>
                    <div className="flex items-center gap-2">
                      <input className="w-1/2 bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="2018" value={edu.year_start || ''} onChange={(e) => updateArray('education', i, 'year_start', e.target.value)} />
                      <span className="text-[var(--text-secondary)]">-</span>
                      <input className="w-1/2 bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="2022" value={edu.year_end || ''} onChange={(e) => updateArray('education', i, 'year_end', e.target.value)} />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-black/60 dark:text-white/60 mb-1.5 block uppercase">CGPA / Grade</label>
                    <input className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" placeholder="3.8/4.0" value={edu.gpa || ''} onChange={(e) => updateArray('education', i, 'gpa', e.target.value)} />
                  </div>
                </div>
              </div>
            ))}
            
            <button 
              onClick={() => addArrayItem('education', { degree: '', institution: '', year_start: '', year_end: '', gpa: '' })} 
              className="w-full py-4 border border-dashed border-black/20 dark:border-white/20 rounded-xl text-black/60 dark:text-white/60 hover:border-indigo-500 hover:text-indigo-500 transition-colors flex items-center justify-center gap-2 text-sm font-medium"
            >
              <Plus className="w-4 h-4"/> Add Education
            </button>
          </div>
        </section>
        
        {/* 7. CERTIFICATIONS & ACHIEVEMENTS */}
        <section id="section-certifications" className="space-y-6 scroll-mt-8">
          <div className="border-b border-[var(--border-color)] pb-2 flex justify-between items-center">
            <h2 className="text-xs font-semibold tracking-widest uppercase text-black dark:text-white border-l-2 border-indigo-500 pl-3 flex items-center gap-2"><Award className="w-5 h-5 text-indigo-500" /> Certifications & Achievements</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Certifications */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold uppercase text-[var(--text-secondary)]">Certifications</h3>
              {(profile.certifications || []).map((cert: any, i: number) => (
                <div key={i} className="flex gap-2">
                  <input 
                    className="flex-1 bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" 
                    placeholder="e.g. AWS Solutions Architect" 
                    value={cert.name || ''} 
                    onChange={(e) => updateArray('certifications', i, 'name', e.target.value)} 
                  />
                  <button onClick={() => removeArrayItem('certifications', i)} className="px-2 text-black/30 hover:text-red-500 dark:text-white/30 dark:hover:text-red-400 transition-colors"><Trash2 className="w-4 h-4"/></button>
                </div>
              ))}
              <button 
                onClick={() => addArrayItem('certifications', { name: '', url: '' })} 
                className="text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 flex items-center gap-1"
              >
                <Plus className="w-4 h-4"/> Add Certification
              </button>
            </div>
            
            {/* Achievements */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold uppercase text-[var(--text-secondary)]">Achievements</h3>
              {(profile.achievements || []).map((achieve: string, i: number) => (
                <div key={i} className="flex gap-2">
                  <input 
                    className="flex-1 bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" 
                    placeholder="e.g. 1st Place at Hackathon" 
                    value={achieve || ''} 
                    onChange={(e) => updateArrayString('achievements', i, e.target.value)} 
                  />
                  <button onClick={() => removeArrayItem('achievements', i)} className="px-2 text-black/30 hover:text-red-500 dark:text-white/30 dark:hover:text-red-400 transition-colors"><Trash2 className="w-4 h-4"/></button>
                </div>
              ))}
              <button 
                onClick={() => addArrayItem('achievements', '')} 
                className="text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 flex items-center gap-1"
              >
                <Plus className="w-4 h-4"/> Add Achievement
              </button>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
};

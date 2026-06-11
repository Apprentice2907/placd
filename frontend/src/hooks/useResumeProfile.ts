import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../lib/api';
import type { ResumeProfile } from '../types/resume';

const DEFAULT_PROFILE: ResumeProfile = {
  id: `prof_${Date.now()}`,
  label: 'Default',
  personal: {
    name: 'Jane Doe', email: 'jane.doe@example.com', phone: '(555) 123-4567', location: 'San Francisco, CA', linkedin: 'linkedin.com/in/janedoe', github: 'github.com/janedoe', portfolio: 'janedoe.dev'
  },
  education: [
    {
      id: 'edu_1',
      institution: 'University of California, Berkeley',
      degree: 'Bachelor of Science',
      field: 'Computer Science',
      graduation_year: '2020',
      gpa: '3.8',
      coursework: ['Data Structures', 'Algorithms', 'Web Development']
    }
  ],
  experience: [
    {
      id: 'exp_1',
      company: 'Tech Solutions Inc.',
      role: 'Frontend Developer',
      start: '2021-06',
      end: 'Present',
      location: 'San Francisco, CA',
      bullets: [
        'Developed and maintained scalable frontend applications using React and TypeScript, improving page load speed by 30%.',
        'Collaborated with cross-functional teams to design and implement new features, resulting in a 15% increase in user engagement.',
        'Mentored junior developers and conducted code reviews to ensure code quality and adherence to best practices.'
      ]
    },
    {
      id: 'exp_2',
      company: 'Web Creatives LLC',
      role: 'Junior Web Developer',
      start: '2020-07',
      end: '2021-05',
      location: 'San Jose, CA',
      bullets: [
        'Assisted in the development of responsive websites using HTML, CSS, and JavaScript, meeting all project deadlines.',
        'Implemented automated testing using Jest, reducing bug reports by 20% in the first quarter.',
        'Participated in daily stand-ups and sprint planning sessions in an Agile environment.'
      ]
    }
  ],
  projects: [
    {
      id: 'proj_1',
      name: 'E-commerce Platform',
      stack: ['React', 'Node.js', 'MongoDB', 'Express'],
      link: 'github.com/janedoe/ecommerce',
      bullets: [
        'Built a full-stack e-commerce application with user authentication, product catalog, and payment gateway integration.',
        'Designed a RESTful API to handle client requests and manage database interactions securely.',
        'Deployed the application using Docker and AWS EC2 for high availability.'
      ]
    }
  ],
  skills: { 
    languages: ['JavaScript', 'TypeScript', 'Python', 'HTML/CSS'], 
    frameworks: ['React', 'Next.js', 'Node.js', 'Express', 'Tailwind CSS'], 
    tools: ['Git', 'Docker', 'Webpack', 'Figma'], 
    databases: ['PostgreSQL', 'MongoDB', 'Redis'] 
  },
  achievements: [
    'Winner of 2019 Hackathon out of 50 participating teams.',
    'Certified AWS Developer Associate.'
  ]
};

export function useResumeProfile(sessionId: string) {
  const [profile, setProfileState] = useState<ResumeProfile>(DEFAULT_PROFILE);
  const [loading, setLoading] = useState(true);
  const timeoutRef = useRef<number | null>(null);

  useEffect(() => {
    let active = true;
    if (!sessionId) {
      setLoading(false);
      return;
    }

    api.profile.get(sessionId).then(data => {
      if (active) {
        if (data && data.resume_profiles && data.resume_profiles.length > 0) {
          setProfileState(data.resume_profiles[0]);
        } else if (data) {
          // Map existing old profile data into new structure
          setProfileState({
            ...DEFAULT_PROFILE,
            personal: {
              name: data.full_name || '',
              email: data.email || '',
              phone: data.phone || '',
              location: data.location || '',
              linkedin: data.linkedin_url || '',
              github: data.github_url || '',
              portfolio: data.portfolio_url || ''
            },
            experience: (data.experiences || []).map((exp: any, i: number) => ({
              id: `exp_${i}`,
              company: exp.company || '',
              role: exp.role || '',
              start: exp.start || '',
              end: exp.end || '',
              location: '',
              bullets: exp.bullets || []
            })),
            education: (data.education || []).map((edu: any, i: number) => ({
              id: `edu_${i}`,
              institution: edu.institution || '',
              degree: edu.degree || '',
              field: edu.field || '',
              graduation_year: edu.year || '',
              gpa: edu.gpa || '',
              coursework: []
            })),
            projects: (data.projects || []).map((p: any, i: number) => ({
              id: `proj_${i}`,
              name: p.name || '',
              stack: p.stack || [],
              link: p.link || '',
              bullets: p.bullets || []
            }))
          });
        }
        setLoading(false);
      }
    }).catch(err => {
      if (active) {
        console.error("Failed to load profile", err);
        setLoading(false);
      }
    });

    return () => { active = false; };
  }, [sessionId]);

  const setProfile = useCallback((newProfile: ResumeProfile) => {
    setProfileState(newProfile);
    
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    timeoutRef.current = window.setTimeout(() => {
      api.profile.upsert({ session_id: sessionId, resume_profiles: [newProfile] }).catch(console.error);
    }, 1000);
  }, [sessionId]);

  return { profile, setProfile, loading };
}

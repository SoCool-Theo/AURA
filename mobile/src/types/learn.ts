export type LearnLesson = {
  id: string;
  title: string;
  category: 'Risk Basics' | 'Portfolio' | 'Analytics' | 'Simulation' | 'AI';
  readMinutes: number;
  summary: string;
  body: string[];
};

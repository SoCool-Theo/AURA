import { go } from '../../app/routes';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { LearningFeature } from './components/LearningFeature';
import { LearningPath } from './components/LearningPath';
import { LessonLibrary } from './components/LessonLibrary';
import type { Lesson } from './components/LessonLibrary';

const LESSONS: Lesson[] = [
  {
    title: 'Understanding Risk Score',
    text: 'How Aura combines volatility, drawdown, concentration, and diversification.',
    icon: 'shield',
    topic: 'Risk basics',
    time: '5 min',
    level: 'Beginner',
  },
  {
    title: 'Volatility',
    text: 'Learn what historical price fluctuations mean for a portfolio.',
    icon: 'trend',
    topic: 'Market behavior',
    time: '4 min',
    level: 'Beginner',
  },
  {
    title: 'Maximum Drawdown',
    text: 'Understand the largest peak-to-trough decline.',
    icon: 'drawdown',
    topic: 'Loss awareness',
    time: '6 min',
    level: 'Beginner',
  },
  {
    title: 'Sharpe Ratio',
    text: 'Learn about return relative to historical volatility.',
    icon: 'analytics',
    topic: 'Risk-adjusted return',
    time: '7 min',
    level: 'Intermediate',
  },
  {
    title: 'Correlation',
    text: 'See why assets moving together can increase concentration risk.',
    icon: 'analysis',
    topic: 'Diversification',
    time: '6 min',
    level: 'Intermediate',
  },
  {
    title: 'Historical What-If',
    text: 'Learn how scenario simulations use past market periods.',
    icon: 'simulations',
    topic: 'Scenarios',
    time: '8 min',
    level: 'Intermediate',
  },
];

export function LearnPage() {
  function openLesson(lesson: Lesson) {
    alert(`${lesson.title}\n\n${lesson.text}\n\nThis learning module can later be connected to your course content or Aura knowledge base.`);
  }

  return (
    <div className="page learn-page">
      <header className="learn-header">
        <div>
          <span>AURA LEARNING CENTER</span>
          <h1>Learn Portfolio Risk</h1>
          <p>Build confidence with clear, beginner-friendly lessons about portfolio behavior.</p>
        </div>
        <div className="learn-progress-pill">
          <span><Icon name="reports" size={18} /></span>
          <div><strong>{LESSONS.length} lessons</strong><small>About 36 minutes total</small></div>
        </div>
      </header>

      <div className="learn-feature-grid">
        <LearningFeature lesson={LESSONS[0]} onOpen={openLesson} />
        <LearningPath />
      </div>

      <LessonLibrary lessons={LESSONS} onOpen={openLesson} />

      <Card className="learn-aura-card">
        <span><Icon name="spark" size={22} /></span>
        <div>
          <h2>Future AI explanations</h2>
          <p>The AI Assistant is a truthful preview until Aura’s backend AI Agent is implemented.</p>
        </div>
        <button className="secondary-btn" onClick={() => go('assistant')}>
          View AI Preview <span>→</span>
        </button>
      </Card>
      <div className="learn-education-note">
        <Icon name="shield" size={16} />
        <p>Learning content explains historical portfolio-risk concepts and is not financial or investment advice.</p>
      </div>
    </div>
  );
}

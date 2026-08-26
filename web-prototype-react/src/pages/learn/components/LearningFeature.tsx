import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import type { Lesson } from './LessonLibrary';

interface LearningFeatureProps {
  lesson: Lesson;
  onOpen: (lesson: Lesson) => void;
}

export function LearningFeature({ lesson, onOpen }: LearningFeatureProps) {
  return (
    <Card className="learn-feature-card">
      <div className="learn-feature-copy">
        <span className="learn-feature-label"><Icon name="spark" size={13} /> RECOMMENDED START</span>
        <h2>Understand what your risk score is really telling you</h2>
        <p>Learn how Aura brings several historical risk measures together without turning them into investment advice.</p>
        <div className="learn-feature-meta">
          <span><Icon name="calendar" size={14} /> 5 minutes</span>
          <span><Icon name="shield" size={14} /> Beginner</span>
        </div>
        <button className="primary-btn" onClick={() => onOpen(lesson)}>
          Start First Lesson <span>→</span>
        </button>
      </div>
      <div className="learn-feature-visual">
        <div className="learning-orbit">
          <span><Icon name="shield" size={32} /></span>
          <i className="orbit-one"><Icon name="trend" size={16} /></i>
          <i className="orbit-two"><Icon name="drawdown" size={16} /></i>
          <i className="orbit-three"><Icon name="analysis" size={16} /></i>
        </div>
        <small>Risk is more than one number</small>
      </div>
    </Card>
  );
}

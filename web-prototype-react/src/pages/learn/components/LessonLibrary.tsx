import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

export interface Lesson {
  title: string;
  text: string;
  icon: string;
  topic: string;
  time: string;
  level: string;
}

interface LessonLibraryProps {
  lessons: Lesson[];
  onOpen: (lesson: Lesson) => void;
}

export function LessonLibrary({ lessons, onOpen }: LessonLibraryProps) {
  return (
    <section className="learning-library">
      <div className="learning-library-heading">
        <div>
          <span>LEARNING LIBRARY</span>
          <h2>Explore all lessons</h2>
          <p>Short explanations designed to make portfolio-risk metrics easier to understand.</p>
        </div>
        <span className="lesson-count">{lessons.length} modules</span>
      </div>
      <div className="lesson-grid">
        {lessons.map((lesson, index) => (
          <Card key={lesson.title} className={`lesson-card lesson-tone-${index % 3}`}>
            <div className="lesson-card-top">
              <span><Icon name={lesson.icon} size={21} /></span>
              <b>{String(index + 1).padStart(2, '0')}</b>
            </div>
            <span className="lesson-topic">{lesson.topic}</span>
            <h3>{lesson.title}</h3>
            <p>{lesson.text}</p>
            <div className="lesson-meta">
              <span><Icon name="calendar" size={13} />{lesson.time}</span>
              <span><Icon name="analysis" size={13} />{lesson.level}</span>
            </div>
            <button onClick={() => onOpen(lesson)}>Open Lesson <span>→</span></button>
          </Card>
        ))}
      </div>
    </section>
  );
}

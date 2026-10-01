import { useMemo, useState } from 'react';
import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

export interface Lesson {
  id: string;
  title: string;
  text: string;
  body: string[];
  video?: {
    title: string;
    url: string;
  };
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
  const [query, setQuery] = useState('');
  const normalizedQuery = query.trim().toLowerCase();
  const filteredLessons = useMemo(() => {
    if (!normalizedQuery) return lessons;
    return lessons.filter((lesson) => [
      lesson.title,
      lesson.topic,
      lesson.text,
      ...lesson.body,
    ].some((value) => value.toLowerCase().includes(normalizedQuery)));
  }, [lessons, normalizedQuery]);

  return (
    <section className="learning-library">
      <div className="learning-library-heading">
        <div>
          <span>LEARNING LIBRARY</span>
          <h2>Explore all lessons</h2>
          <p>Short explanations designed to make portfolio-risk metrics easier to understand.</p>
        </div>
        <span className="lesson-count">{filteredLessons.length} of {lessons.length} modules</span>
      </div>
      <label className="lesson-search">
        <span className="lesson-search-icon"><Icon name="search" size={17} /></span>
        <span className="sr-only">Search lessons</span>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search lessons by topic or concept…"
        />
      </label>
      <div className="lesson-grid">
        {filteredLessons.map((lesson) => {
          const index = lessons.findIndex((item) => item.id === lesson.id);
          return (
          <Card key={lesson.id} className={`lesson-card lesson-tone-${index % 4}`}>
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
          );
        })}
      </div>
      {filteredLessons.length === 0 && (
        <div className="lesson-search-empty" role="status">
          <Icon name="search" size={22} />
          <strong>No lessons found</strong>
          <p>Try another topic, metric, or keyword.</p>
          <button type="button" onClick={() => setQuery('')}>Clear search</button>
        </div>
      )}
    </section>
  );
}

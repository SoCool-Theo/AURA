import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Icon } from '../../../components/ui/Icon';
import type { Lesson } from './LessonLibrary';

type LessonDialogProps = {
  lesson: Lesson;
  onClose: () => void;
};

export function LessonDialog({ lesson, onClose }: LessonDialogProps) {
  const dialogRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  const titleId = `lesson-${lesson.id}-title`;
  const summaryId = `lesson-${lesson.id}-summary`;
  onCloseRef.current = onClose;

  useEffect(() => {
    returnFocusRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeButtonRef.current?.focus();

    function handleKeys(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onCloseRef.current();
        return;
      }
      if (event.key !== 'Tab') return;
      const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), a[href]',
      ) ?? []);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    window.addEventListener('keydown', handleKeys);
    return () => {
      window.removeEventListener('keydown', handleKeys);
      document.body.style.overflow = previousOverflow;
      returnFocusRef.current?.focus();
    };
  }, [lesson.id]);

  return createPortal(
    <div className="learn-lesson-overlay">
      <button
        type="button"
        className="learn-lesson-backdrop"
        aria-label="Close lesson"
        onClick={onClose}
      />
      <section
        ref={dialogRef}
        className="learn-lesson-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={summaryId}
      >
        <header className="learn-lesson-dialog-header">
          <div>
            <span>{lesson.topic.toUpperCase()}</span>
            <h2 id={titleId}>{lesson.title}</h2>
            <p>{lesson.time} · {lesson.level}</p>
          </div>
          <button ref={closeButtonRef} type="button" aria-label="Close lesson" onClick={onClose}>×</button>
        </header>

        <div className="learn-lesson-dialog-body">
          <p id={summaryId} className="learn-lesson-summary">{lesson.text}</p>
          <div className="learn-lesson-copy">
            {lesson.body.map((paragraph, index) => (
              <p key={index} className={paragraph.startsWith('Example:') ? 'learn-lesson-example' : undefined}>
                {paragraph}
              </p>
            ))}
          </div>

          {lesson.video && (
            <div className="learn-lesson-video">
              <span><Icon name="pulse" size={18} /></span>
              <div>
                <small>RELATED VIDEO</small>
                <strong>{lesson.video.title}</strong>
              </div>
              <a href={lesson.video.url} target="_blank" rel="noreferrer">
                Watch on YouTube <span aria-hidden="true">↗</span>
              </a>
            </div>
          )}
        </div>
      </section>
    </div>,
    document.body,
  );
}

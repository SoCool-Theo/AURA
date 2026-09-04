import type { ReactNode } from "react";

export function SectionCard({ title, description, action, children, className = "" }: {
  title?: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`aura-card ${className}`}>
      {(title || action) && (
        <header className="card-head">
          <div>{title && <h2>{title}</h2>}{description && <p>{description}</p>}</div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

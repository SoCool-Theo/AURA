import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Icon } from '../../../components/ui/Icon';
import styles from './AboutAuraDialog.module.css';

const features = [
  ['Portfolios & risk', 'Explore current holdings or planned allocations and understand returns, volatility, drawdown, diversification, and risk drivers.'],
  ['What-if simulations', 'Compare hypothetical allocation changes and historical scenarios without changing your original portfolio.'],
  ['AI Assistant', "Ask for plain-language explanations grounded in Aura's portfolio analysis and simulation results."],
  ['Watchlist & Learn', 'Follow supported assets using saved market observations and learn with simple financial examples. Watchlist prices are not live quotes.'],
];

export function AboutAuraDialog({ onClose }: { onClose: () => void }) {
  const dialogRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeRef.current?.focus();
    function handleKeys(event: KeyboardEvent) {
      if (event.key === 'Escape') { onCloseRef.current(); return; }
      if (event.key !== 'Tab') return;
      const buttons = Array.from(dialogRef.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? []);
      const first = buttons[0], last = buttons[buttons.length - 1];
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    }
    window.addEventListener('keydown', handleKeys);
    return () => {
      window.removeEventListener('keydown', handleKeys);
      document.body.style.overflow = previousOverflow;
      if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
    };
  }, []);

  return createPortal(
    <div className={styles.overlay}>
      <button type="button" className={styles.backdrop} aria-label="Close About Aura" onClick={onClose} />
      <section ref={dialogRef} className={styles.dialog} role="dialog" aria-modal="true" aria-labelledby="about-aura-title" aria-describedby="about-aura-summary">
        <header className={styles.header}>
          <span className={styles.brandIcon}><Icon name="shield" size={24} /></span>
          <div><small>PORTFOLIO RISK EDUCATION</small><h2 id="about-aura-title">About Aura</h2></div>
          <button ref={closeRef} type="button" className={styles.close} aria-label="Close About Aura" onClick={onClose}><Icon name="close" size={20} /></button>
        </header>
        <div className={styles.body}>
          <p id="about-aura-summary">Aura helps you understand the risks inside a portfolio and make sense of financial results in everyday language.</p>
          <div className={styles.features}>{features.map(([title, description]) => <section key={title}><h3>{title}</h3><p>{description}</p></section>)}</div>
          <div className={styles.notice}><Icon name="school" size={20} /><p>Aura is a portfolio risk education platform, not a trading platform or financial advisor. Historical results do not guarantee future performance; Aura does not provide buy/sell recommendations.</p></div>
        </div>
        <footer className={styles.footer}><button type="button" className="primary-btn" onClick={onClose}>Done</button></footer>
      </section>
    </div>, document.body,
  );
}

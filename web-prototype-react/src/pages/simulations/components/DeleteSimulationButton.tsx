import { useEffect, useRef, useState } from 'react';
import { deleteSimulationHistory } from '../../../api/simulationsApi';
import { ConfirmationDialog } from '../../../components/ui/ConfirmationDialog';
import styles from '../SimulationIntegration.module.css';

export function DeleteSimulationButton({ portfolioId, simulationId, subject, onDeleted }: {
  portfolioId: string; simulationId: string; subject: string; onDeleted: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const busyRef = useRef(false);
  const mountedRef = useRef(true);
  useEffect(() => { mountedRef.current = true; return () => { mountedRef.current = false; }; }, []);

  async function remove() {
    if (!open || busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError(null);
    try {
      await deleteSimulationHistory(portfolioId, simulationId);
      if (mountedRef.current) { setOpen(false); onDeleted(); }
    } catch (caught) {
      if (mountedRef.current) setError(caught);
    } finally {
      busyRef.current = false;
      if (mountedRef.current) setBusy(false);
    }
  }

  return <>
    <button type="button" aria-label={`Delete simulation ${subject}`} className={styles.deleteButton} disabled={busy} onClick={() => { setError(null); setOpen(true); }}>Delete Simulation</button>
    {open && <ConfirmationDialog title="Delete simulation?"
      description="This permanently removes this saved simulation and cannot be undone. Your portfolio and analysis reports stay unchanged."
      subjectLabel="Saved simulation" subject={subject} confirmLabel="Delete Simulation" busy={busy} error={error}
      onCancel={() => { if (!busyRef.current) { setOpen(false); setError(null); } }} onConfirm={() => void remove()} />}
  </>;
}

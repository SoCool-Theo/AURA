import React, { useEffect, useRef, useState } from 'react';
import { Button } from '../ui/Button';
import { ConfirmationDialog } from '../ui/ConfirmationDialog';
import { useSimulations } from '../../simulation/useSimulations';
import { simulationErrorMessage } from '../../simulation/simulationErrors';

export function DeleteSimulationButton({ portfolioId, simulationId, subject, onDeleted }: {
  portfolioId: string; simulationId: string; subject: string; onDeleted?: () => void;
}) {
  const { deleteSimulation } = useSimulations();
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
      await deleteSimulation(portfolioId, simulationId);
      if (mountedRef.current) { setOpen(false); onDeleted?.(); }
    } catch (caught) {
      if (mountedRef.current) setError(caught);
    } finally {
      busyRef.current = false;
      if (mountedRef.current) setBusy(false);
    }
  }

  return <>
    <Button title="Delete Simulation" accessibilityLabel={`Delete simulation ${subject}`} variant="danger" disabled={busy} onPress={() => { setError(null); setOpen(true); }} />
    <ConfirmationDialog visible={open} title="Delete simulation?"
      description="This permanently removes this saved simulation and cannot be undone. Your portfolio and analysis reports stay unchanged."
      subjectLabel="Saved simulation" subject={subject} confirmLabel="Delete Simulation" busy={busy}
      errorMessage={error ? simulationErrorMessage(error, 'Unable to delete simulation.') : null}
      onCancel={() => { if (!busyRef.current) { setOpen(false); setError(null); } }} onConfirm={() => void remove()} />
  </>;
}

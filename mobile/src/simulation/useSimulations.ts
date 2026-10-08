import { useContext } from 'react';

import { SimulationContext } from './SimulationProvider';

export function useSimulations() {
  const value = useContext(SimulationContext);
  if (!value) {
    throw new Error('useSimulations must be used inside SimulationProvider');
  }
  return value;
}

import { useContext } from 'react';

import { PortfolioContext } from './PortfolioProvider';

export function usePortfolios() {
  const value = useContext(PortfolioContext);
  if (!value) {
    throw new Error('usePortfolios must be used inside PortfolioProvider');
  }
  return value;
}

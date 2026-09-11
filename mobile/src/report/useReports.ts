import { useContext } from 'react';

import { ReportContext } from './ReportProvider';

export function useReports() {
  const value = useContext(ReportContext);
  if (!value) {
    throw new Error('useReports must be used inside ReportProvider');
  }
  return value;
}

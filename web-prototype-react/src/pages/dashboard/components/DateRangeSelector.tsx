import { Icon } from '../../../components/ui/Icon';

export function DateRangeSelector({ startDate, endDate }: { startDate?: string; endDate?: string }) {
  return <div className="dashboard-selector date-selector" aria-label="Latest report period"><Icon name="calendar" size={19} /><span>{startDate && endDate ? `${startDate} – ${endDate}` : 'No analysis period'}</span></div>;
}

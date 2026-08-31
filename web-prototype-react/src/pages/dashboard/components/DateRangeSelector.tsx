import { Icon } from '../../../components/ui/Icon';
import styles from '../DashboardIntegration.module.css';

export function DateRangeSelector({ startDate, endDate }: { startDate?: string; endDate?: string }) {
  return <div className={`dashboard-selector date-selector ${styles.analysisPeriod}`} aria-label="Latest report analysis period"><Icon name="calendar" size={19} /><span><small>Latest report period</small><strong>{startDate && endDate ? `${startDate} – ${endDate}` : 'No analysis period'}</strong></span></div>;
}

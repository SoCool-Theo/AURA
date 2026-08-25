import { Icon } from '../../../components/ui/Icon';

export function DateRangeSelector() {
  return (
    <button
      className="dashboard-selector date-selector"
      aria-label="Selected date: May 11, 2026"
    >
      <Icon name="calendar" size={19} />
      <span>May 11, 2026</span>
      <span className="selector-chevron"><Icon name="chevron-down" size={17} /></span>
    </button>
  );
}

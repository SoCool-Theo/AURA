import type { AllocationSimulationComparison } from '../../../types/simulation';
import { Card } from '../../../components/ui/Card';
import { formatNumber, formatPercent } from '../simulationUi';
import styles from '../SimulationIntegration.module.css';

export function SimulationComparison({ comparison }: { comparison: AllocationSimulationComparison }) {
  const items: Array<[string, string, number | null]> = [
    ['Ending normalized value', 'number', comparison.normalized_ending_value_delta],
    ['Cumulative return', 'percent', comparison.cumulative_return_delta],
    ['Annualized volatility', 'percent', comparison.annualized_volatility_delta],
    ['Sharpe ratio', 'number', comparison.sharpe_ratio_delta],
    ['Maximum drawdown', 'percent', comparison.maximum_drawdown_delta],
  ];
  return <Card className="simulation-comparison-card"><div className="simulation-card-heading"><div><h2>Allocation Comparison</h2><p>Each difference is the modified allocation result minus the original allocation result.</p></div></div><div className={styles.metrics}>{items.map(([label, type, value]) => <Card className={styles.metric} key={label}><small>{label}</small><strong className={value !== null && value < 0 ? styles.negative : ''}>{type === 'percent' && value !== null ? formatPercent(value) : formatNumber(value)}</strong><span>Modified − original</span></Card>)}</div></Card>;
}

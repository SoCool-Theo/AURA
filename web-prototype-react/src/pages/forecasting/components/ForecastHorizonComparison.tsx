import { useState } from 'react';
import { Card } from '../../../components/ui/Card';
import type { ForecastHorizon, OutlookResponse } from '../../../types/forecasting';
import { comparisonPoints, forecastHorizons, forecastPercent, forecastReturn, forecastVolatility, forecastWarnings, type OutlookMetric } from '../forecastingUi';
import { OutlookChart } from './OutlookChart';
import styles from '../Forecasting.module.css';

export function ForecastHorizonComparison({ results, loading, unavailable }: {
  results: OutlookResponse[]; loading: boolean; unavailable: ForecastHorizon[];
}) {
  const [metric, setMetric] = useState<OutlookMetric>('return');
  const warnings = forecastWarnings(results);
  return <Card className={styles.section}>
    <div className={styles.sectionHeading}><div><h2>Compare forecast horizons</h2><p>Independent 7-, 14-, 21- and 30-calendar-day backend estimates.</p></div>
      <div className={styles.segmented} role="group" aria-label="Comparison chart metric">{(['return', 'volatility'] as const).map(value => <button type="button" key={value} aria-pressed={metric === value} className={metric === value ? styles.active : ''} onClick={() => setMetric(value)}>{value === 'return' ? 'Expected Return' : 'Volatility'}</button>)}</div>
    </div>
    <p className={styles.qualityNotice}>Weekly points are experimental and not approved as reliable predictions. Each horizon has different models and calibration; this is not one daily forecast trajectory.</p>
    {loading && <p className={styles.note} role="status">Loading horizon comparisons…</p>}
    {unavailable.length > 0 && <p className={styles.note} role="status">Unavailable: {unavailable.map(day => `${day} days`).join(', ')}. Missing points are not estimated or replaced. Use Refresh Outlook to retry.</p>}
    {results.length > 0 && <OutlookChart points={comparisonPoints(results, metric)} metric={metric} />}
    <div className={styles.tableScroll} role="region" aria-label="Forecast horizon comparison" tabIndex={0}><table className={`${styles.table} ${styles.comparisonTable}`}><thead><tr><th>Horizon</th><th>Expected return</th><th>Forecast volatility</th><th>Market data as of</th><th>Status</th></tr></thead><tbody>{forecastHorizons.map(day => {
      const result = results.find(item => item.horizon_days === day);
      return <tr key={day}><td>{day} days</td><td className={result && forecastReturn(result) < 0 ? styles.negative : ''}>{result ? forecastPercent(forecastReturn(result), true) : '—'}</td><td>{result ? forecastPercent(forecastVolatility(result)) : '—'}</td><td>{result?.market_data_as_of ?? '—'}</td><td>{result ? day === 30 ? 'V1 Preview' : 'Experimental Weekly V1' : unavailable.includes(day) ? 'Unavailable' : loading ? 'Loading…' : 'Not loaded'}</td></tr>;
    })}</tbody></table></div>
    <p className={styles.note}>Amber markers identify weekly estimates; teal identifies 30 days. Lines connect only adjacent available horizons with matching market-data dates. Dates may differ across horizons; review each row before comparing.</p>
    {warnings.length > 0 && <details className={styles.comparisonWarnings}><summary>Model-quality warnings ({warnings.length})</summary><ul className={styles.limitations}>{warnings.map(warning => <li key={warning.key}><b>{warning.label}:</b> {warning.message}</li>)}</ul></details>}
  </Card>;
}

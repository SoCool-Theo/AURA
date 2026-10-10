import { useState } from 'react';
import { Card } from '../../../components/ui/Card';
import { usePortfolioPrivacy, usePrivateValue } from '../../../privacy/PortfolioPrivacy';
import type { ForecastHorizon, OutlookResponse } from '../../../types/forecasting';
import { comparisonPoints, forecastMoney, negativeMoney, forecastHorizons, forecastPercent, forecastReturn, forecastVolatility, forecastWarnings, type OutlookMetric } from '../forecastingUi';
import { OutlookChart } from './OutlookChart';
import styles from '../Forecasting.module.css';

export function ForecastHorizonComparison({ results, loading, unavailable }: {
  results: OutlookResponse[]; loading: boolean; unavailable: ForecastHorizon[];
}) {
  const [metric, setMetric] = useState<OutlookMetric>('return');
  const { hideValues } = usePortfolioPrivacy();
  const privateValue = usePrivateValue();
  const firstMoney = results.flatMap(item => 'portfolio_id' in item && item.monetary_projection ? [item.monetary_projection] : [])[0];
  const showAmounts = Boolean(firstMoney);
  const canChartMoney = showAmounts && !hideValues && results.every(item => 'portfolio_id' in item && item.monetary_projection?.currency === firstMoney.currency);
  const activeMetric = metric === 'change' && !canChartMoney ? 'return' : metric;
  const chartMetrics: OutlookMetric[] = canChartMoney ? ['return', 'change', 'volatility'] : ['return', 'volatility'];
  const points = comparisonPoints(results, activeMetric);
  const warnings = forecastWarnings(results);
  return <Card className={styles.section}>
    <div className={styles.sectionHeading}><div><h2>Compare forecast horizons</h2><p>Independent 7-, 14-, 21- and 30-calendar-day backend estimates.</p></div>
      <div className={styles.segmented} role="group" aria-label="Comparison chart metric">{chartMetrics.map(value => <button type="button" key={value} aria-pressed={activeMetric === value} className={activeMetric === value ? styles.active : ''} onClick={() => setMetric(value)}>{value === 'return' ? 'Expected Return' : value === 'change' ? `Expected change (${firstMoney.currency})` : 'Volatility'}</button>)}</div>
    </div>
    <p className={styles.qualityNotice}>Weekly points are experimental and not approved as reliable predictions. Each horizon has different models and calibration; this is not one daily forecast trajectory.</p>
    {loading && <p className={styles.note} role="status">Loading horizon comparisons…</p>}
    {unavailable.length > 0 && <p className={styles.note} role="status">Unavailable: {unavailable.map(day => `${day} days`).join(', ')}. Missing points are not estimated or replaced. Use Refresh Outlook to retry.</p>}
    {points.length > 0 && <OutlookChart points={points} metric={activeMetric} />}
    <div className={styles.tableScroll} role="region" aria-label="Forecast horizon comparison" tabIndex={0}><table className={`${styles.table} ${styles.comparisonTable}`}><thead><tr><th>Horizon</th><th>Expected return</th>{showAmounts && <><th>Baseline amount</th><th>Expected change</th><th>Estimated value</th></>}<th>Forecast volatility</th><th>Market data as of</th><th>Status</th></tr></thead><tbody>{forecastHorizons.map(day => {
      const result = results.find(item => item.horizon_days === day);
      const money = result && 'portfolio_id' in result ? result.monetary_projection : null;
      return <tr key={day}><td>{day} days</td><td className={result && forecastReturn(result) < 0 ? styles.negative : ''}>{result ? forecastPercent(forecastReturn(result), true) : '—'}</td>
        {showAmounts && <><td>{money ? privateValue(`${forecastMoney(money.baseline_amount, money.currency)} ${money.currency}`) : '—'}</td><td className={money && negativeMoney(money.expected_change_amount) ? styles.negative : ''}>{money ? privateValue(forecastMoney(money.expected_change_amount, money.currency, true)) : '—'}</td><td>{money ? privateValue(forecastMoney(money.estimated_ending_value, money.currency)) : '—'}</td></>}
        <td>{result ? forecastPercent(forecastVolatility(result)) : '—'}</td><td>{result?.market_data_as_of ?? '—'}</td><td>{result ? day === 30 ? 'V1 Preview' : 'Experimental Weekly V1' : unavailable.includes(day) ? 'Unavailable' : loading ? 'Loading…' : 'Not loaded'}</td></tr>;
    })}</tbody></table></div>
    {showAmounts && <p className={styles.note}>Each horizon uses its own returned baseline amount. Planned amounts are hypothetical; THB assumes unchanged FX. Amounts are estimates, not guaranteed balances. Monetary lines do not connect different baselines or currencies.{hideValues && ' Amounts and monetary charts are hidden by your privacy setting.'}</p>}
    {activeMetric === 'change' && points.length < results.length && <p className={styles.note}>Some amounts cannot be plotted at the supported chart scale. Their exact amounts remain in the table.</p>}
    <p className={styles.note}>Amber markers identify weekly estimates; teal identifies 30 days. Lines connect only adjacent available horizons with matching market-data dates. Dates may differ across horizons; review each row before comparing.</p>
    {warnings.length > 0 && <details className={styles.comparisonWarnings}><summary>Model-quality warnings ({warnings.length})</summary><ul className={styles.limitations}>{warnings.map(warning => <li key={warning.key}><b>{warning.label}:</b> {warning.message}</li>)}</ul></details>}
  </Card>;
}

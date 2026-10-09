import { useState } from 'react';
import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';
import { usePortfolioPrivacy, usePrivateValue } from '../../../privacy/PortfolioPrivacy';
import type { OutlookResponse } from '../../../types/forecasting';
import { forecastBaselineLabel, forecastMoney, negativeMoney, forecastPercent, forecastPoints, forecastReturn, forecastVolatility, forecastWarnings, type OutlookMetric } from '../forecastingUi';
import { OutlookChart } from './OutlookChart';
import styles from '../Forecasting.module.css';

export function ForecastingResults({ result, showChart = true }: { result: OutlookResponse; showChart?: boolean }) {
  const [metric, setMetric] = useState<OutlookMetric>('return');
  const asset = 'symbol' in result;
  const money = asset ? null : result.monetary_projection;
  const { hideValues } = usePortfolioPrivacy();
  const privateValue = usePrivateValue();
  const activeMetric = metric === 'change' && (!money || hideValues) ? 'return' : metric;
  const chartMetrics: OutlookMetric[] = money && !hideValues ? ['return', 'change', 'volatility'] : ['return', 'volatility'];
  const points = forecastPoints(result, activeMetric);
  const components = asset ? [] : result.components;
  const expectedReturn = forecastReturn(result);
  const volatility = forecastVolatility(result);
  const warnings = forecastWarnings([result]);
  // Chart geometry only; signed backend-owned contributions remain unchanged.
  const negative = Math.min(0, ...components.map(item => item.forecast_volatility_contribution_share));
  const positive = Math.max(0, ...components.map(item => item.forecast_volatility_contribution_share));
  const span = positive - negative || 1;
  const zero = (-negative / span) * 100;
  return <div className={styles.results}>
    {result.horizon_days !== 30 && <div className={styles.qualityNotice}><strong>Experimental Weekly V1 · educational use only</strong><p>Mixed per-asset quality. Not approved as reliable predictions. Nominal 80% ranges do not imply 80% achieved accuracy.</p>{warnings.length > 0 && <ul>{warnings.map(warning => <li key={warning.key}><b>{warning.label}:</b> {warning.message}</li>)}</ul>}</div>}
    <Card className={styles.context}>
      <div><span className={styles.eyebrow}>{asset ? 'ASSET OUTLOOK' : 'PORTFOLIO OUTLOOK'}</span><h2>{asset ? result.symbol : result.portfolio_name}</h2><p>{asset ? 'Standalone asset estimate · ownership is not required' : forecastBaselineLabel(result.baseline_kind)}</p></div>
      <div className={styles.metadata}><span>Market data as of <strong>{result.market_data_as_of}</strong></span><span>Model version <strong>{result.artifact_version}</strong></span>{asset ? <span>Forecast origin <strong>{result.forecast_origin_date} · {result.market_data_age_days} calendar days old</strong></span> : <span>Correlation data <strong>{result.correlation_as_of_date} · {result.correlation_observation_count} common observations</strong></span>}</div>
    </Card>
    <div className={styles.metrics}>
      <Card className={styles.metric}><span>Expected {result.horizon_days}-Day Return</span><strong className={expectedReturn < 0 ? styles.negative : styles.accent}>{forecastPercent(expectedReturn, true)}</strong><small>Model estimate, not a guaranteed outcome.</small>{asset && <p>80% prediction range: <b>{forecastPercent(result.return_prediction_interval.lower)} to {forecastPercent(result.return_prediction_interval.upper)}</b></p>}</Card>
      <Card className={styles.metric}><span>Forecast {result.horizon_days}-Day Volatility</span><strong className={styles.accent}>{forecastPercent(volatility)}</strong><small>Non-annualized · not comparable directly with annualized historical volatility.</small>{asset && <p>80% prediction range: <b>{forecastPercent(result.volatility_prediction_interval.lower)} to {forecastPercent(result.volatility_prediction_interval.upper)}</b></p>}</Card>
    </div>
    {money && <Card className={styles.section}>
      <div className={styles.sectionHeading}><div><h2>Portfolio amount outlook</h2><p>{money.hypothetical ? 'Hypothetical planned investment' : 'Current portfolio market value'} · {money.currency} · backend-calculated estimates</p></div></div>
      <div className={styles.moneyMetrics}>
        <div><span>{money.hypothetical ? 'Planned investment' : 'Current portfolio value'}</span><strong>{privateValue(forecastMoney(money.baseline_amount, money.currency))}</strong></div>
        <div><span>Expected {result.horizon_days}-day change</span><strong className={negativeMoney(money.expected_change_amount) ? styles.negative : styles.accent}>{privateValue(forecastMoney(money.expected_change_amount, money.currency, true))}</strong></div>
        <div><span>Estimated {result.horizon_days}-day value</span><strong>{privateValue(forecastMoney(money.estimated_ending_value, money.currency))}</strong></div>
      </div>
      <p className={styles.note}>{money.hypothetical ? 'Based on the investment amounts you entered, not assets you currently own.' : `Based on saved prices × owned shares, not purchase cost. Valuation requested ${money.valuation_requested_date}; prices from ${money.oldest_price_as_of} to ${money.newest_price_as_of}.`} {money.assumes_unchanged_fx && 'THB estimates assume unchanged exchange rates; this is not an FX forecast.'} Amounts are estimates, not guaranteed balances. Fees, taxes and cash flows are excluded.</p>
      {hideValues && <p className={styles.note}>Amounts are hidden by your privacy setting. The amount chart is hidden too.</p>}
    </Card>}
    {!asset && result.baseline_kind === 'legacy' && <p className={styles.note}>Legacy saved weights do not establish an investment amount. This Outlook remains percentage-only.</p>}
    {showChart && <Card className={styles.section}>
      <div className={styles.sectionHeading}><div><h2>Outlook by horizon</h2><p>{result.horizon_days} calendar days · selected backend estimate</p></div><div className={styles.segmented} role="group" aria-label="Forecast chart metric">{chartMetrics.map(value => <button type="button" key={value} aria-pressed={activeMetric === value} className={activeMetric === value ? styles.active : ''} onClick={() => setMetric(value)}>{value === 'return' ? 'Expected Return' : value === 'change' ? `Expected change (${money?.currency})` : 'Volatility'}</button>)}</div></div>
      {points.length ? <OutlookChart points={points} metric={activeMetric} /> : <p className={styles.note}>This amount cannot be plotted at the supported chart scale. Review the exact amount above.</p>}
    </Card>}
    {!asset && <>
      <Card className={styles.section}><div className={styles.sectionHeading}><div><h2>Forecast Risk Contributors</h2><p>Share of forecast portfolio volatility · negative contributions are preserved.</p></div></div>
        <div className={styles.drivers}>{components.map(item => {
          const share = item.forecast_volatility_contribution_share;
          return <div className={styles.driver} key={item.symbol}><button type="button" onClick={() => go(`forecasting/asset/${encodeURIComponent(item.symbol)}`)}>{item.symbol} ↗</button><div className={styles.track}><i className={styles.origin} style={{ left: zero + '%' }} /><i className={share < 0 ? styles.negativeBar : styles.positiveBar} style={{ left: share < 0 ? ((share - negative) / span) * 100 + '%' : zero + '%', width: Math.abs(share) / span * 100 + '%' }} /></div><strong>{forecastPercent(share, true)}</strong></div>;
        })}</div><p className={styles.note}>Negative contributions can offset other components in this covariance-based estimate. Correlations may change.</p>
      </Card>
      <Card className={styles.section}>
        <div className={styles.sectionHeading}><div><h2>Asset breakdown</h2><p>Backend-resolved allocation, individual forecasts, and signed contributions.</p></div></div>
        <div className={styles.tableScroll} role="region" aria-label="Portfolio outlook components" tabIndex={0}><table className={styles.table}><thead><tr>
          <th>Asset</th><th>Allocation</th>{money && <th>{money.hypothetical ? 'Planned amount' : 'Current value'} ({money.currency})</th>}<th>{result.horizon_days}-day return</th>{money && <th>Estimated value ({money.currency})</th>}<th>{result.horizon_days}-day volatility</th><th>Volatility contribution</th><th>Origin</th><th>Action</th>
        </tr></thead><tbody>{components.map(item => {
          const holding = item.monetary_projection;
          return <tr key={item.symbol}>
            <td><strong>{item.symbol}</strong></td><td>{forecastPercent(item.current_weight)}</td>
            {money && <td>{holding ? privateValue(forecastMoney(holding.baseline_amount, holding.currency)) : '—'}</td>}
            <td className={forecastReturn(item) < 0 ? styles.negative : ''}>{forecastPercent(forecastReturn(item), true)}{holding && <small className={styles.cellAmount}>Change: {privateValue(forecastMoney(holding.expected_change_amount, holding.currency, true))}</small>}</td>
            {money && <td>{holding ? privateValue(forecastMoney(holding.estimated_ending_value, holding.currency)) : '—'}</td>}
            <td>{forecastPercent(forecastVolatility(item))}</td><td>{forecastPercent(item.forecast_volatility_contribution, true)}</td>
            <td>{item.forecast_origin_date}{holding?.oldest_price_as_of && <small className={styles.cellAmount}>Price: {holding.oldest_price_as_of}</small>}</td>
            <td><button type="button" onClick={() => go(`forecasting/asset/${encodeURIComponent(item.symbol)}`)}>View Outlook →</button></td>
          </tr>;
        })}</tbody></table></div>
        <p className={styles.note}>{money && 'Each amount uses that holding’s own baseline and forecast return, not the overall portfolio return. '}Component forecasts can have different origins. The portfolio market-data date is the oldest component date. Asset drill-down opens the standalone default 30-day view without your holding amount; select a weekly horizon there.</p>
      </Card>
    </>}
    <Card className={styles.section}><details><summary>Model details and limitations</summary>{asset ? <dl className={styles.modelDetails}><div><dt>Return model</dt><dd>{result.return_model_id}</dd></div><div><dt>Volatility model</dt><dd>{result.volatility_model_id}</dd></div></dl> : <div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>Asset</th><th>Return model</th><th>Volatility model</th></tr></thead><tbody>{components.map(item => <tr key={item.symbol}><td>{item.symbol}</td><td>{item.return_model_id}</td><td>{item.volatility_model_id}</td></tr>)}</tbody></table></div>}<ul className={styles.limitations}>{result.limitations.map(item => <li key={item}>{item}</li>)}</ul>{money && <><h3 className={styles.assumptionHeading}>Monetary assumptions</h3><ul className={styles.limitations}>{money.limitations.map(item => <li key={item}>{item}</li>)}</ul></>}</details></Card>
  </div>;
}

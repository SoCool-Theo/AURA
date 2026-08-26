import { useEffect, useState } from 'react';
import { go } from '../../app/routes';
import { LineChart } from '../../components/charts/LineChart';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { RiskPill } from '../../components/ui/RiskPill';
import { SymbolBadge } from '../../components/ui/SymbolBadge';
import { loadReportDetailSnapshot } from '../../mocks/reports.mock';
import type {
  ReportAssetDetail,
  ReportDetail,
  ReportMetric,
  ReportRiskDriver,
} from '../../types/report';
import { money } from '../../utils/formatting';
import styles from './ReportDetailPage.module.css';

type ReportTab = 'overview' | 'risk-drivers' | 'asset-details' | 'correlations';

interface ReportDetailPageProps {
  portfolioId: string;
  reportId: string;
}

const tabs: ReadonlyArray<{ id: ReportTab; label: string }> = [
  { id: 'overview', label: 'Overview' },
  { id: 'risk-drivers', label: 'Risk Drivers' },
  { id: 'asset-details', label: 'Asset Details' },
  { id: 'correlations', label: 'Correlations' },
];

function formatMetric(metric: ReportMetric): string {
  if (metric.format === 'currency') return money(metric.value);
  if (metric.format === 'percentage') {
    const positivePrefix = metric.label === 'Annualized Return' && metric.value > 0 ? '+' : '';
    return `${positivePrefix}${metric.value.toFixed(2)}%`;
  }
  if (metric.format === 'score') return `${metric.value}/100`;
  return metric.value.toFixed(2);
}

function ReportMetricGrid({ report }: { report: ReportDetail }) {
  return (
    <Card className={styles.metricsCard}>
      <div className={styles.sectionHeading}>
        <div><h2>Key Metrics</h2><p>Saved values from this analysis snapshot.</p></div>
        <RiskPill score={report.riskScore} />
      </div>
      <div className={styles.metricGrid}>
        <article className={`${styles.metric} ${styles.red}`}>
          <div className={styles.metricLabel}><Icon name="shield" size={16} /> Risk Score</div>
          <strong>{report.riskScore}</strong>
          <span>{report.riskLevel} portfolio risk</span>
          <div className={styles.scoreTrack} aria-hidden="true"><i style={{ width: `${report.riskScore}%` }} /></div>
        </article>
        {report.metrics.map(metric => (
          <article key={metric.label} className={`${styles.metric} ${styles[metric.tone]}`}>
            <div className={styles.metricLabel}><Icon name={metric.icon} size={16} /> {metric.label}</div>
            <strong>{formatMetric(metric)}</strong>
            <span>{metric.detail}</span>
          </article>
        ))}
        <article className={`${styles.metric} ${styles.blue}`}>
          <div className={styles.metricLabel}><Icon name="analytics" size={16} /> Correlation (Avg.)</div>
          <strong>{report.correlation.averageCorrelation.toFixed(2)}</strong>
          <span>Saved average correlation</span>
        </article>
      </div>
    </Card>
  );
}

function ReportSummaryCard({ report }: { report: ReportDetail }) {
  const rows = [
    ['Report Type', report.reportType],
    ['Portfolio', report.portfolioName],
    ['Analysis Period', report.analysisPeriod],
    ['Created', report.createdAt],
    ['Risk Classification', report.riskLevel],
    ['Timeframe', report.performance.periodLabel === 'ALL' ? 'All Time' : report.performance.periodLabel],
    ['Version', report.version],
    ['Status', report.status],
  ];

  return (
    <Card className={styles.summaryCard}>
      <div className={styles.cardTitle}><h2>Report Summary</h2></div>
      <dl>
        {rows.map(([label, value]) => (
          <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
        ))}
      </dl>
    </Card>
  );
}

function PerformanceCard({ report }: { report: ReportDetail }) {
  const { performance } = report;

  return (
    <Card className={styles.performanceCard}>
      <div className={styles.sectionHeading}>
        <div><h2>Portfolio Performance</h2><p>{report.analysisPeriod}</p></div>
        <span className={styles.rangeBadge}>ALL</span>
      </div>
      <div className={styles.chartArea}>
        <LineChart
          primary={[...performance.values]}
          labels={[...performance.labels]}
          height={250}
          area
        />
      </div>
      <dl className={styles.performanceStats}>
        <div><dt>Start Value</dt><dd>{money(performance.startValue)}</dd></div>
        <div><dt>End Value</dt><dd>{money(performance.endValue)}</dd></div>
        <div><dt>Period Return</dt><dd className={styles.positive}>+{performance.periodReturn.toFixed(2)}%</dd></div>
        <div><dt>Annualized Return</dt><dd className={styles.positive}>+{performance.annualizedReturn.toFixed(2)}%</dd></div>
      </dl>
    </Card>
  );
}

function CompactRiskDrivers({ drivers }: { drivers: ReadonlyArray<ReportRiskDriver> }) {
  return (
    <Card className={styles.compactDrivers}>
      <div className={styles.cardTitle}><h2>Top Risk Drivers</h2></div>
      <div className={styles.compactDriverHeader} aria-hidden="true">
        <span>Asset</span><span>Weight</span><span>Contribution</span><span>Impact</span>
      </div>
      {drivers.slice(0, 4).map(driver => (
        <div className={styles.compactDriverRow} key={driver.symbol}>
          <div className={styles.assetIdentity}>
            <SymbolBadge symbol={driver.symbol} />
            <span><strong>{driver.symbol}</strong><small>{driver.name}</small></span>
          </div>
          <b>{driver.weight.toFixed(1)}%</b>
          <b>{driver.riskContribution.toFixed(1)}%</b>
          <RiskPill score={driver.impactScore} />
        </div>
      ))}
    </Card>
  );
}

function RiskDriversPanel({ drivers }: { drivers: ReadonlyArray<ReportRiskDriver> }) {
  return (
    <Card className={styles.tabCard}>
      <div className={styles.sectionHeading}>
        <div><h2>Risk Drivers</h2><p>Saved contribution and impact values ordered by portfolio influence.</p></div>
      </div>
      <div className={styles.driverList}>
        {drivers.map(driver => (
          <article key={driver.symbol} className={styles.driverDetail}>
            <span className={styles.rank}>{driver.rank}</span>
            <div className={styles.assetIdentity}>
              <SymbolBadge symbol={driver.symbol} />
              <span><strong>{driver.symbol}</strong><small>{driver.name}</small></span>
            </div>
            <dl>
              <div><dt>Portfolio Weight</dt><dd>{driver.weight.toFixed(1)}%</dd></div>
              <div><dt>Risk Contribution</dt><dd>{driver.riskContribution.toFixed(1)}%</dd></div>
            </dl>
            <RiskPill score={driver.impactScore} />
            <p>{driver.explanation}</p>
          </article>
        ))}
      </div>
    </Card>
  );
}

function AssetCard({ asset }: { asset: ReportAssetDetail }) {
  return (
    <Card className={styles.assetCard}>
      <header>
        <div className={styles.assetIdentity}>
          <SymbolBadge symbol={asset.symbol} />
          <span><strong>{asset.symbol}</strong><small>{asset.name}</small></span>
        </div>
        <RiskPill score={asset.riskScore} />
      </header>
      <p className={styles.assetType}>{asset.assetType} · {asset.weight.toFixed(1)}% allocation</p>
      <dl>
        <div><dt>Saved Value</dt><dd>{money(asset.value)}</dd></div>
        <div><dt>Annualized Return</dt><dd>{asset.annualizedReturn.toFixed(2)}%</dd></div>
        <div><dt>Annualized Volatility</dt><dd>{asset.annualizedVolatility.toFixed(2)}%</dd></div>
        <div><dt>Maximum Drawdown</dt><dd className={styles.negative}>{asset.maxDrawdown.toFixed(2)}%</dd></div>
      </dl>
    </Card>
  );
}

function AssetDetailsPanel({ assets }: { assets: ReadonlyArray<ReportAssetDetail> }) {
  return (
    <section aria-labelledby="asset-details-heading">
      <div className={styles.panelHeading}>
        <h2 id="asset-details-heading">Asset Details</h2>
        <p>Per-asset values captured when this report was generated.</p>
      </div>
      <div className={styles.assetGrid}>{assets.map(asset => <AssetCard key={asset.symbol} asset={asset} />)}</div>
    </section>
  );
}

function CorrelationPanel({ report }: { report: ReportDetail }) {
  const { symbols, matrix, averageCorrelation, note } = report.correlation;

  return (
    <Card className={styles.tabCard}>
      <div className={styles.sectionHeading}>
        <div><h2>Asset Correlations</h2><p>Saved relationships between the report's principal holdings.</p></div>
        <span className={styles.averageBadge}>Average {averageCorrelation.toFixed(2)}</span>
      </div>
      <div className={styles.heatmapWrap} role="region" aria-label="Asset correlation matrix" tabIndex={0}>
        <table className={styles.heatmap}>
          <thead><tr><th aria-label="Asset" />{symbols.map(symbol => <th key={symbol}>{symbol}</th>)}</tr></thead>
          <tbody>
            {matrix.map((row, rowIndex) => (
              <tr key={symbols[rowIndex]}>
                <th scope="row">{symbols[rowIndex]}</th>
                {row.map((cell, columnIndex) => (
                  <td key={symbols[columnIndex]} className={styles[cell.tone]}>{cell.value.toFixed(2)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className={styles.correlationNote}><Icon name="shield" size={18} /><p>{note}</p></div>
    </Card>
  );
}

function OverviewPanel({ report }: { report: ReportDetail }) {
  return (
    <div className={styles.overviewLayout}>
      <div className={styles.mainColumn}>
        <ReportMetricGrid report={report} />
        <PerformanceCard report={report} />
      </div>
      <aside className={styles.sideColumn} aria-label="Report summary">
        <ReportSummaryCard report={report} />
        <CompactRiskDrivers drivers={report.riskDrivers} />
        <Card className={styles.notesCard}>
          <div className={styles.cardTitle}><h2>Report Information</h2></div>
          <p>{report.summary}</p>
          <small>Historical results are educational and do not guarantee future performance.</small>
        </Card>
      </aside>
    </div>
  );
}

function LoadingState() {
  return <div className={styles.state} role="status"><span className={styles.spinner} /><h2>Loading report</h2><p>Retrieving the saved analysis snapshot.</p></div>;
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className={styles.state} role="alert">
      <span className={styles.stateIcon}><Icon name="reports" size={29} /></span>
      <h2>We couldn’t load this report</h2>
      <p>Try again, or return to your saved reports.</p>
      <div><button className="primary-btn" onClick={onRetry}>Try Again</button><button className="secondary-btn" onClick={() => go('reports')}>Back to Reports</button></div>
    </div>
  );
}

function MissingState() {
  return (
    <div className={styles.state}>
      <span className={styles.stateIcon}><Icon name="search" size={29} /></span>
      <h2>Report not found</h2>
      <p>This report does not exist for the selected portfolio or is no longer available.</p>
      <button className="primary-btn" onClick={() => go('reports')}>Back to Reports</button>
    </div>
  );
}

export function ReportDetailPage({ portfolioId, reportId }: ReportDetailPageProps) {
  const [activeTab, setActiveTab] = useState<ReportTab>('overview');
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [requestKey, setRequestKey] = useState(0);

  useEffect(() => {
    let current = true;
    setLoading(true);
    setError(false);
    setReport(null);

    loadReportDetailSnapshot(portfolioId, reportId)
      .then(snapshot => {
        if (current) setReport(snapshot);
      })
      .catch(() => {
        if (current) setError(true);
      })
      .finally(() => {
        if (current) setLoading(false);
      });

    return () => { current = false; };
  }, [portfolioId, reportId, requestKey]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState onRetry={() => setRequestKey(key => key + 1)} />;
  if (!report) return <MissingState />;

  function moveTab(currentTab: ReportTab, direction: -1 | 1) {
    const currentIndex = tabs.findIndex(tab => tab.id === currentTab);
    const nextTab = tabs[(currentIndex + direction + tabs.length) % tabs.length];
    setActiveTab(nextTab.id);
    document.getElementById(`report-tab-${nextTab.id}`)?.focus();
  }

  return (
    <div className={`page ${styles.page}`}>
      <button className={styles.backLink} onClick={() => go('reports')}>← Reports <span>/</span> Report Details</button>
      <header className={styles.header}>
        <div>
          <div className={styles.titleRow}><h1>{report.title}</h1><span>Analysis</span></div>
          <p>{report.portfolioName}<i>•</i>{report.createdAt}</p>
        </div>
        <div className={styles.headerActions} aria-label="Report actions">
          <button className="secondary-btn" disabled title="PDF export will be available after backend integration">Download PDF</button>
          <button className="secondary-btn" disabled title="CSV export will be available after backend integration">Download CSV</button>
        </div>
      </header>

      <div className={styles.tabs} role="tablist" aria-label="Report sections">
        {tabs.map(tab => (
          <button
            key={tab.id}
            id={`report-tab-${tab.id}`}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`report-panel-${tab.id}`}
            tabIndex={activeTab === tab.id ? 0 : -1}
            className={activeTab === tab.id ? styles.active : ''}
            onClick={() => setActiveTab(tab.id)}
            onKeyDown={event => {
              if (event.key === 'ArrowRight') { event.preventDefault(); moveTab(tab.id, 1); }
              if (event.key === 'ArrowLeft') { event.preventDefault(); moveTab(tab.id, -1); }
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div
        id={`report-panel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`report-tab-${activeTab}`}
        className={styles.tabPanel}
      >
        {activeTab === 'overview' && <OverviewPanel report={report} />}
        {activeTab === 'risk-drivers' && <RiskDriversPanel drivers={report.riskDrivers} />}
        {activeTab === 'asset-details' && <AssetDetailsPanel assets={report.assets} />}
        {activeTab === 'correlations' && <CorrelationPanel report={report} />}
      </div>
    </div>
  );
}

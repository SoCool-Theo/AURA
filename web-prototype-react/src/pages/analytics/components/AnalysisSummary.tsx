import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';
import type { PortfolioAnalysisResponse } from '../../../types/analytics';
import { formatNumber } from '../analyticsUi';
import styles from '../AnalyticsIntegration.module.css';

interface AnalysisSummaryProps {
  analysis: PortfolioAnalysisResponse;
}

export function AnalysisSummary({ analysis }: AnalysisSummaryProps) {
  const classification = analysis.risk_classification;
  const scoreTone = classification.risk_level === 'Low'
    ? styles.successScore
    : classification.risk_level === 'Moderate'
      ? styles.warningScore
      : styles.dangerScore;

  return (
    <Card className={styles.hero}>
      <div>
        <span className={styles.eyebrow}>SAVED ANALYSIS SNAPSHOT</span>
        <h2>{analysis.portfolio_name}</h2>
        <p>
          Requested period {analysis.start_date} through {analysis.end_date}; available
          observations span {analysis.metadata.analysis_start} through {analysis.metadata.analysis_end}.
        </p>
        <ul className={styles.reasons}>
          {classification.reasons.map(reason => <li key={reason}>{reason}</li>)}
        </ul>
      </div>
      <div className={`${styles.score} ${scoreTone}`}>
        <Icon name="speedometer" size={22} />
        <strong>{formatNumber(classification.risk_score, 1)}</strong>
        <span>{classification.risk_level} risk</span>
      </div>
    </Card>
  );
}

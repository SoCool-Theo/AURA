import type { Portfolio } from '../../../types/portfolio';
import { go } from '../../../app/routes';
import { Card } from '../../../components/ui/Card';

interface ActivityTabProps {
  portfolio: Portfolio;
}

const ACTIVITY_ITEMS = [
  'Portfolio analyzed — risk score 72',
  '2008 Financial Crisis simulation completed',
  'Holding weight updated for NVDA',
  'Portfolio created',
];

function Timeline({ items }: { items: string[] }) {
  return (
    <div className="timeline">
      {items.map((item, index) => (
        <div key={item}>
          <span>{index + 1}</span>
          <div>
            <strong>{item}</strong>
            <small>{index === 0 ? 'Today' : `${index} day${index > 1 ? 's' : ''} ago`}</small>
          </div>
        </div>
      ))}
    </div>
  );
}

export function ActivityTab({ portfolio }: ActivityTabProps) {
  return (
    <div className="detail-tab-panel activity-tab-layout">
      <Card className="detail-activity-card">
        <div className="detail-card-heading"><div><h2>Recent Activity</h2><p>Portfolio changes, analyses, and simulations.</p></div></div>
        <Timeline items={ACTIVITY_ITEMS} />
      </Card>
      <Card className="activity-summary-card">
        <div className="detail-card-heading"><div><h2>Portfolio History</h2><p>Current record summary</p></div></div>
        <dl>
          <div><dt>Created</dt><dd>{new Date(portfolio.created).toLocaleDateString()}</dd></div>
          <div><dt>Last analyzed</dt><dd>May 11, 2026</dd></div>
          <div><dt>Saved reports</dt><dd>2</dd></div>
          <div><dt>Simulations</dt><dd>1</dd></div>
        </dl>
        <button className="secondary-btn" onClick={() => go('reports')}>View Reports <span>→</span></button>
      </Card>
    </div>
  );
}

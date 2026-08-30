import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

export function AiInsight() {
  return <Card className="dashboard-insight-card"><div className="dashboard-card-header"><div className="dashboard-card-title"><span className="title-icon"><Icon name="spark" size={21} /></span><h2>AI Explanation</h2></div></div><p>Aura’s backend AI explanation service is not available yet. Dashboard metrics currently come only from deterministic saved analysis reports.</p></Card>;
}

import { Card } from '../../../components/ui/Card';
import { Icon } from '../../../components/ui/Icon';

export function AiInsight() {
  return <Card className="dashboard-insight-card"><div className="dashboard-card-header"><div className="dashboard-card-title"><span className="title-icon"><Icon name="spark" size={21} /></span><h2>AI Explanation</h2></div></div><p>Ask Aura can explain saved risk results in plain language after an analysis is available.</p></Card>;
}

import { Card } from '../../../components/ui/Card';

export function LearningPath({ learnProgress = {} }: { learnProgress?: Record<string, boolean> }) {
  const counts = [
    ['risk-score', 'volatility', 'drawdown', 'sharpe'],
    ['diversification'],
    ['historical-scenario', 'allocation-change', 'combined', 'ai-explanation'],
  ].map(ids => ids.filter(id => learnProgress[id]).length);
  const active = counts.findIndex((count, index) => count < [4, 1, 4][index]);
  return (
    <Card className="learning-path-card">
      <div className="learning-path-heading">
        <span>YOUR LEARNING PATH</span>
        <h2>From foundations to scenarios</h2>
        <p>Follow the modules in order or explore any topic.</p>
      </div>
      <div className="learning-path-steps">
        <div className={active === 0 ? 'active' : undefined}>
          <span>1</span>
          <div><strong>Risk Foundations</strong><small>Score, volatility, drawdown, and Sharpe ratio</small></div>
          <b>{counts[0]}/4 completed</b>
        </div>
        <div className={active === 1 ? 'active' : undefined}>
          <span>2</span>
          <div><strong>Portfolio Relationships</strong><small>Weights, concentration, and diversification</small></div>
          <b>{counts[1]}/1 completed</b>
        </div>
        <div className={active === 2 ? 'active' : undefined}>
          <span>3</span>
          <div><strong>Aura Tools</strong><small>Simulations and grounded AI explanations</small></div>
          <b>{counts[2]}/4 completed</b>
        </div>
      </div>
    </Card>
  );
}

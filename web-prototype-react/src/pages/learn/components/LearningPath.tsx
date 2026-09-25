import { Card } from '../../../components/ui/Card';

export function LearningPath() {
  return (
    <Card className="learning-path-card">
      <div className="learning-path-heading">
        <span>YOUR LEARNING PATH</span>
        <h2>From foundations to scenarios</h2>
        <p>Follow the modules in order or explore any topic.</p>
      </div>
      <div className="learning-path-steps">
        <div className="active">
          <span>1</span>
          <div><strong>Risk Foundations</strong><small>Score, volatility, drawdown, and Sharpe ratio</small></div>
          <b>4 lessons</b>
        </div>
        <div>
          <span>2</span>
          <div><strong>Portfolio Relationships</strong><small>Weights, concentration, and diversification</small></div>
          <b>1 lesson</b>
        </div>
        <div>
          <span>3</span>
          <div><strong>Aura Tools</strong><small>Simulations and grounded AI explanations</small></div>
          <b>4 lessons</b>
        </div>
      </div>
    </Card>
  );
}

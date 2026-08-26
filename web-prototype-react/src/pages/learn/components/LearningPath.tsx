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
          <div><strong>Risk Foundations</strong><small>Score, volatility, and drawdown</small></div>
          <b>3 lessons</b>
        </div>
        <div>
          <span>2</span>
          <div><strong>Portfolio Relationships</strong><small>Return, correlation, diversification</small></div>
          <b>2 lessons</b>
        </div>
        <div>
          <span>3</span>
          <div><strong>Historical Scenarios</strong><small>Understand what-if simulations</small></div>
          <b>1 lesson</b>
        </div>
      </div>
    </Card>
  );
}

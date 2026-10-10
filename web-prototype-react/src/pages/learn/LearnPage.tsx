import { useState } from 'react';
import { useLearnProgress } from '../../learn/LearnProgress';
import { go } from '../../app/routes';
import { Card } from '../../components/ui/Card';
import { Icon } from '../../components/ui/Icon';
import { LearningFeature } from './components/LearningFeature';
import { LearningPath } from './components/LearningPath';
import { LessonDialog } from './components/LessonDialog';
import { LessonLibrary } from './components/LessonLibrary';
import type { Lesson } from './components/LessonLibrary';

const LESSONS: Lesson[] = [
  {
    id: 'risk-score',
    title: 'What does a portfolio risk score mean?',
    text: 'Understand why Aura combines multiple risk signals instead of relying on one number.',
    body: [
      'A portfolio risk score is a compact way to summarize several dimensions of risk.',
      'Aura combines factors such as volatility, drawdown, concentration and diversification into one educational score.',
      'Use the score as an educational summary, then open the detailed metrics to understand why the score is high or low.',
      'Example: two portfolios may both return 8%, but a portfolio that regularly swings 25% and keeps 60% in one stock would usually show more risk than one that swings 12% and spreads its holdings more evenly.',
    ],
    video: {
      title: 'Index Funds, Risk, & Compounding: Investing Basics — Vanguard',
      url: 'https://www.youtube.com/watch?v=8hfisvspufQ',
    },
    icon: 'speedometer',
    topic: 'Risk Basics',
    time: '4 min',
    level: 'Beginner',
  },
  {
    id: 'volatility',
    title: 'Volatility in simple terms',
    text: 'Learn what volatility says about how strongly portfolio values tend to move.',
    body: [
      'Volatility describes how widely returns move around their average.',
      'Higher volatility means the portfolio has experienced larger fluctuations. Lower volatility means the historical path has generally been steadier.',
      'Volatility does not tell you whether an investment is good or bad. It is one risk signal that should be interpreted together with drawdown, diversification and other metrics.',
      'Example: Portfolio A moves by about +1% or -1% each month, while Portfolio B moves by +8%, -7% and +6%. Even if their average returns are similar, Portfolio B has been more volatile.',
    ],
    video: {
      title: 'Volatility Explained in One Minute — One Minute Economics',
      url: 'https://www.youtube.com/watch?v=EOG-jZ-qxUE',
    },
    icon: 'pulse',
    topic: 'Analytics',
    time: '3 min',
    level: 'Beginner',
  },
  {
    id: 'drawdown',
    title: 'Maximum drawdown',
    text: 'See how drawdown captures the largest historical peak-to-trough decline.',
    body: [
      'Maximum drawdown measures the largest fall from a previous portfolio peak to a later trough.',
      'A drawdown of -20% means the portfolio once fell 20% from its earlier high before recovering or reaching the end of the measured period.',
      'Drawdown is especially useful because it describes downside experience in a way that is easy to connect to real portfolio stress.',
      'Example: if a portfolio falls from a $10,000 peak to $8,000, its drawdown is 20%. It then needs a 25% gain from $8,000 to return to $10,000.',
    ],
    video: {
      title: 'Maximum Drawdown Explained in 3 Minutes — letYourMoneyGrow.com',
      url: 'https://www.youtube.com/watch?v=sgqQWb3tT6U',
    },
    icon: 'drawdown',
    topic: 'Analytics',
    time: '4 min',
    level: 'Beginner',
  },
  {
    id: 'sharpe',
    title: 'Sharpe ratio',
    text: 'Understand the relationship between return and volatility.',
    body: [
      'The Sharpe ratio is a risk-adjusted return metric.',
      'In simple terms, it asks how much return a portfolio produced relative to the amount of volatility it experienced.',
      'Aura explains this result in context so users do not treat one ratio as a complete investment decision.',
      'Example: with an 8% return, a 2% risk-free rate and 10% volatility, the simplified Sharpe ratio is (8% - 2%) / 10% = 0.6. The same return with 20% volatility gives 0.3, showing less return per unit of volatility.',
    ],
    video: {
      title: 'Sharpe Ratio Explained — Corporate Finance Institute',
      url: 'https://www.youtube.com/watch?v=rdhDmQOUMUE',
    },
    icon: 'stats-chart',
    topic: 'Analytics',
    time: '5 min',
    level: 'Intermediate',
  },
  {
    id: 'diversification',
    title: 'Diversification and concentration',
    text: 'Learn why portfolio weights and relationships between assets matter.',
    body: [
      'Diversification is about spreading exposure so that one asset or one type of market movement does not dominate the whole portfolio.',
      'A portfolio can hold many assets and still be concentrated if one holding has a very large weight or several assets behave similarly.',
      'Aura highlights concentration, correlations and risk drivers to make those relationships easier to understand.',
      'Example: placing $6,000 of a $10,000 portfolio in one stock creates a 60% concentration. Five equal holdings may look more balanced, but they can still be concentrated if all five are technology stocks that tend to move together.',
    ],
    video: {
      title: 'What Is Diversification? — Fidelity Investments',
      url: 'https://www.youtube.com/watch?v=MZchH0Ddzn8',
    },
    icon: 'diversification',
    topic: 'Portfolio',
    time: '5 min',
    level: 'Intermediate',
  },
  {
    id: 'historical-scenario',
    title: 'Historical Scenario simulation',
    text: 'Understand what Aura means by testing today’s allocation during a past event.',
    body: [
      'Historical Scenario keeps the saved portfolio allocation unchanged and evaluates it over a predefined historical event.',
      'It is a what-if education tool, not a forecast of what will happen next.',
      'Aura keeps the requested event dates separate from the effective dates available after historical-data alignment.',
      'Example: if a saved $10,000 allocation ends the selected past event at $8,500, Aura is showing how that allocation behaved in that historical window—not predicting that it will lose 15% next time.',
    ],
    icon: 'simulations',
    topic: 'Simulation',
    time: '4 min',
    level: 'Intermediate',
  },
  {
    id: 'allocation-change',
    title: 'Allocation Change simulation',
    text: 'Compare the saved weights with another set of percentages.',
    body: [
      'Allocation Change asks how historical risk and performance would differ if the same assets had different weights.',
      'Aura compares the original and modified allocations using the same historical period and aligned market data.',
      'This helps users understand sensitivity to concentration and diversification without presenting a buy or sell recommendation.',
      'Example: compare a 70% stock / 30% bond allocation with a 50% stock / 50% bond allocation over the same saved period. The difference shows the historical effect of changing weights, not which mix you should choose.',
    ],
    icon: 'compare',
    topic: 'Simulation',
    time: '4 min',
    level: 'Intermediate',
  },
  {
    id: 'combined',
    title: 'Combined Simulation',
    text: 'Compare original and changed allocations during one historical event.',
    body: [
      'Combined Simulation joins the Historical Scenario and Allocation Change ideas.',
      'The user selects a predefined historical event and a modified allocation, then Aura compares both versions under the same event.',
      'The purpose is educational comparison rather than prediction.',
      'Example: Aura can compare the original 70/30 allocation and a proposed 50/50 allocation during the same past market shock so the effect of the allocation change is easier to isolate.',
    ],
    icon: 'assets',
    topic: 'Simulation',
    time: '4 min',
    level: 'Intermediate',
  },
  {
    id: 'ai-explanation',
    title: 'What does the Aura AI Agent do?',
    text: 'Learn the role and boundaries of grounded AI explanations.',
    body: [
      'Aura’s AI Agent explains saved portfolio analysis and supported simulation context in simple language.',
      'The Assistant uses the selected portfolio and its saved analysis to keep explanations relevant to the user’s results.',
      'The Assistant explains Aura’s results. It does not predict prices or provide personalized buy, sell or hold recommendations.',
      'Example: if your saved report shows an 18% maximum drawdown, you can ask the Assistant what that means. It can explain the result and its limitations, but it will not tell you to buy or sell an asset.',
    ],
    icon: 'assistant',
    topic: 'AI',
    time: '3 min',
    level: 'Beginner',
  },
];

export function LearnPage() {
  const { learnProgress, localError, retryLocalData } = useLearnProgress();
  const completed = LESSONS.filter(lesson => learnProgress[lesson.id]).length;
  const percent = Math.round(completed / LESSONS.length * 100);
  const [selectedLesson, setSelectedLesson] = useState<Lesson | null>(null);

  return (
    <div className="page learn-page">
      <header className="learn-header">
        <div>
          <span>AURA LEARNING CENTER</span>
          <h1>Learn Portfolio Risk</h1>
          <p>Build confidence with clear, beginner-friendly lessons about portfolio behavior.</p>
        </div>
        <div className="learn-progress-pill">
          <span><Icon name="school" size={18} /></span>
          <div><strong>{localError ? 'Progress unavailable' : `${completed}/${LESSONS.length} lessons completed`}</strong><small>Saved for this account in this browser</small></div>
        </div>
      </header>
      {localError ? <div role="alert" className="learn-progress-error">{localError} <button className="secondary-btn" onClick={retryLocalData}>Retry local progress</button></div>
        : <div className="learn-progress-track" role="progressbar" aria-label="Lessons completed" aria-valuemin={0} aria-valuemax={LESSONS.length} aria-valuenow={completed}><span style={{ width: `${percent}%` }} /></div>}

      <div className="learn-feature-grid">
        <LearningFeature lesson={LESSONS[0]} onOpen={setSelectedLesson} completed={Boolean(learnProgress[LESSONS[0].id])} />
        <LearningPath learnProgress={learnProgress} />
      </div>

      <LessonLibrary lessons={LESSONS} onOpen={setSelectedLesson} learnProgress={learnProgress} />

      <Card className="learn-aura-card">
        <span><Icon name="spark" size={22} /></span>
        <div>
          <h2>Ask Aura about your results</h2>
          <p>The AI Assistant can explain your saved analysis and simulation results while keeping its educational boundaries clear.</p>
        </div>
        <button className="secondary-btn" onClick={() => go('assistant')}>
          Open AI Assistant <span>→</span>
        </button>
      </Card>
      <div className="learn-education-note">
        <Icon name="shield" size={16} />
        <p>Learning content explains historical portfolio-risk concepts and is not financial or investment advice.</p>
      </div>
      {selectedLesson && <LessonDialog lesson={selectedLesson} onClose={() => setSelectedLesson(null)} />}
    </div>
  );
}

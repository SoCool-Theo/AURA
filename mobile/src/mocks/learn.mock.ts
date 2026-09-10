import type { LearnLesson } from '../types/learn';

export const learnLessons: LearnLesson[] = [
  {
    id: 'risk-score',
    title: 'What does a portfolio risk score mean?',
    category: 'Risk Basics',
    readMinutes: 4,
    summary: 'Understand why Aura combines multiple risk signals instead of relying on one number.',
    body: [
      'A portfolio risk score is a compact way to summarize several dimensions of risk.',
      'Aura’s production backend combines factors such as volatility, drawdown, concentration and diversification. The mobile frontend should display that result rather than recreate the official calculation.',
      'Use the score as an educational summary, then open the detailed metrics to understand why the score is high or low.'
    ]
  },
  {
    id: 'volatility',
    title: 'Volatility in simple terms',
    category: 'Analytics',
    readMinutes: 3,
    summary: 'Learn what volatility says about how strongly portfolio values tend to move.',
    body: [
      'Volatility describes how widely returns move around their average.',
      'Higher volatility means the portfolio has experienced larger fluctuations. Lower volatility means the historical path has generally been steadier.',
      'Volatility does not tell you whether an investment is good or bad. It is one risk signal that should be interpreted together with drawdown, diversification and other metrics.'
    ]
  },
  {
    id: 'drawdown',
    title: 'Maximum drawdown',
    category: 'Analytics',
    readMinutes: 4,
    summary: 'See how drawdown captures the largest historical peak-to-trough decline.',
    body: [
      'Maximum drawdown measures the largest fall from a previous portfolio peak to a later trough.',
      'A drawdown of -20% means the portfolio once fell 20% from its earlier high before recovering or reaching the end of the measured period.',
      'Drawdown is especially useful because it describes downside experience in a way that is easy to connect to real portfolio stress.'
    ]
  },
  {
    id: 'sharpe',
    title: 'Sharpe ratio',
    category: 'Analytics',
    readMinutes: 5,
    summary: 'Understand the relationship between return and volatility.',
    body: [
      'The Sharpe ratio is a risk-adjusted return metric.',
      'In simple terms, it asks how much return a portfolio produced relative to the amount of volatility it experienced.',
      'Aura should present the backend result and explain it in context rather than encouraging users to treat one ratio as a complete investment decision.'
    ]
  },
  {
    id: 'diversification',
    title: 'Diversification and concentration',
    category: 'Portfolio',
    readMinutes: 5,
    summary: 'Learn why portfolio weights and relationships between assets matter.',
    body: [
      'Diversification is about spreading exposure so that one asset or one type of market movement does not dominate the whole portfolio.',
      'A portfolio can hold many assets and still be concentrated if one holding has a very large weight or several assets behave similarly.',
      'Aura highlights concentration, correlations and risk drivers to make those relationships easier to understand.'
    ]
  },
  {
    id: 'historical-scenario',
    title: 'Historical Scenario simulation',
    category: 'Simulation',
    readMinutes: 4,
    summary: 'Understand what Aura means by testing today’s allocation during a past event.',
    body: [
      'Historical Scenario keeps the saved portfolio allocation unchanged and evaluates it over a predefined historical event.',
      'It is a what-if education tool, not a forecast of what will happen next.',
      'Aura keeps the requested event dates separate from the effective dates available after historical-data alignment.'
    ]
  },
  {
    id: 'allocation-change',
    title: 'Allocation Change simulation',
    category: 'Simulation',
    readMinutes: 4,
    summary: 'Compare the saved weights with another set of percentages.',
    body: [
      'Allocation Change asks how historical risk and performance would differ if the same assets had different weights.',
      'The production backend compares the original and modified allocations using the same historical period and aligned market data.',
      'This helps users understand sensitivity to concentration and diversification without presenting a buy or sell recommendation.'
    ]
  },
  {
    id: 'combined',
    title: 'Combined Simulation',
    category: 'Simulation',
    readMinutes: 4,
    summary: 'Compare original and changed allocations during one historical event.',
    body: [
      'Combined Simulation joins the Historical Scenario and Allocation Change ideas.',
      'The user selects a predefined historical event and a modified allocation, then Aura compares both versions under the same event.',
      'The purpose is educational comparison rather than prediction.'
    ]
  },
  {
    id: 'ai-explanation',
    title: 'What does the Aura AI Agent do?',
    category: 'AI',
    readMinutes: 3,
    summary: 'Learn the role and boundaries of grounded AI explanations.',
    body: [
      'Aura’s AI Agent explains saved portfolio analysis and supported simulation context in simple language.',
      'The mobile Assistant sends a selected portfolio ID and question to Aura’s authenticated backend. The backend owns the grounded context, provider access, guardrails, sources and limitations.',
      'The assistant explains backend results rather than replacing the deterministic analytics engine. It does not predict prices or provide personalized buy, sell or hold recommendations.'
    ]
  }
];

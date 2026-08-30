import type { Portfolio } from '../types/portfolio';
import type { PortfolioAnalysis } from '../types/analytics';
import type { SimulationMetrics } from '../types/simulation';
import type { ScenarioDefinition } from '../mocks/scenarios.mock';

function holdingRiskValue(level: 'Low' | 'Medium' | 'High') {
  if (level === 'High') return 90;
  if (level === 'Medium') return 58;
  return 22;
}

export function demoAnalyzePortfolio(portfolio: Portfolio): PortfolioAnalysis {
  if (!portfolio.holdings.length) {
    return {
      riskScore: 0,
      riskLevel: 'Low Risk',
      volatility: 0,
      annualizedReturn: 0,
      maxDrawdown: 0,
      sharpeRatio: 0,
      diversification: 'No holdings',
      topRiskDrivers: []
    };
  }

  const weightedRisk = portfolio.holdings.reduce(
    (sum, holding) => sum + holdingRiskValue(holding.risk) * (holding.weight / 100),
    0
  );
  const maxWeight = Math.max(...portfolio.holdings.map((holding) => holding.weight));
  const concentrationPenalty = Math.max(0, maxWeight - 25) * 0.65;
  const riskScore = Math.max(0, Math.min(100, Math.round(weightedRisk + concentrationPenalty)));

  const volatility = Number((5 + riskScore * 0.18).toFixed(2));
  const annualizedReturn = Number((3.5 + riskScore * 0.14).toFixed(2));
  const maxDrawdown = Number((-(4 + riskScore * 0.22)).toFixed(2));
  const sharpeRatio = volatility ? Number((annualizedReturn / volatility).toFixed(2)) : 0;

  const diversification =
    portfolio.holdings.length >= 5 && maxWeight <= 30
      ? 'Strong'
      : portfolio.holdings.length >= 3 && maxWeight <= 45
        ? 'Moderate'
        : 'Weak';

  const topRiskDrivers = [...portfolio.holdings]
    .map((holding) => ({
      symbol: holding.symbol,
      level: holding.risk,
      score: holdingRiskValue(holding.risk) * (holding.weight / 100),
      explanation:
        holding.risk === 'High'
          ? `${holding.symbol} combines higher demo volatility with a ${holding.weight.toFixed(1)}% portfolio weight.`
          : holding.weight >= 30
            ? `${holding.symbol} has a large ${holding.weight.toFixed(1)}% allocation, increasing concentration.`
            : `${holding.symbol} contributes less risk because of its smaller weight or lower risk profile.`
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 4)
    .map(({ score: _score, ...driver }) => driver);

  return {
    riskScore,
    riskLevel: riskScore >= 70 ? 'High Risk' : riskScore >= 40 ? 'Moderate Risk' : 'Low Risk',
    volatility,
    annualizedReturn,
    maxDrawdown,
    sharpeRatio,
    diversification,
    topRiskDrivers
  };
}

export function demoScenarioMetrics(
  portfolio: Portfolio,
  scenario: ScenarioDefinition
): SimulationMetrics {
  const analysis = demoAnalyzePortfolio(portfolio);
  const sensitivity = 0.65 + analysis.riskScore / 170;
  const cumulativeReturn = Number((scenario.baseImpact * sensitivity).toFixed(2));
  const annualizedVolatility = Number((analysis.volatility * 1.45 + Math.abs(scenario.baseImpact) * 0.3).toFixed(2));
  const maxDrawdown = Number((Math.min(cumulativeReturn * 1.18, cumulativeReturn - 2)).toFixed(2));
  const sharpeRatio = annualizedVolatility
    ? Number((cumulativeReturn / annualizedVolatility).toFixed(2))
    : null;
  const endingValue = Number((portfolio.totalValue * (1 + cumulativeReturn / 100)).toFixed(2));

  return { cumulativeReturn, annualizedVolatility, maxDrawdown, sharpeRatio, endingValue };
}

export function portfolioWithWeights(
  portfolio: Portfolio,
  weights: Record<string, number>
): Portfolio {
  return {
    ...portfolio,
    holdings: portfolio.holdings.map((holding) => ({
      ...holding,
      weight: weights[holding.symbol] ?? holding.weight
    }))
  };
}

export function demoAllocationMetrics(
  portfolio: Portfolio,
  weights: Record<string, number>
): SimulationMetrics {
  const modified = portfolioWithWeights(portfolio, weights);
  const analysis = demoAnalyzePortfolio(modified);
  const cumulativeReturn = Number((4.5 + analysis.riskScore * 0.105).toFixed(2));
  const annualizedVolatility = analysis.volatility;
  const maxDrawdown = analysis.maxDrawdown;
  const sharpeRatio = annualizedVolatility
    ? Number((cumulativeReturn / annualizedVolatility).toFixed(2))
    : null;
  const endingValue = Number((portfolio.totalValue * (1 + cumulativeReturn / 100)).toFixed(2));
  return { cumulativeReturn, annualizedVolatility, maxDrawdown, sharpeRatio, endingValue };
}

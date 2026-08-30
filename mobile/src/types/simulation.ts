export type SimulationMode = 'Historical Scenario' | 'Allocation Change' | 'Combined';

export type SimulationMetrics = {
  cumulativeReturn: number;
  annualizedVolatility: number;
  maxDrawdown: number;
  sharpeRatio: number | null;
  endingValue: number;
};

export type SimulationRecord = {
  id: string;
  portfolioId: string;
  portfolioName: string;
  mode: SimulationMode;
  title: string;
  createdAt: string;
  scenarioId?: string;
  original: SimulationMetrics;
  modified?: SimulationMetrics;
  comparison?: {
    returnDelta: number;
    volatilityDelta: number;
    drawdownDelta: number;
  };
};

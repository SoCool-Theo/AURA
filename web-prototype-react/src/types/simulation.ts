export type ScenarioOption = {
  id: string;
  label: string;
  dates: string;
  returnPct: number;
  drawdown: number;
  volatility: number;
  recovery: number;
};

export type SimulationMode = 'Historical Scenario' | 'Allocation Change' | 'Combined Simulation';

export type SimulationAllocation = Record<string, number>;

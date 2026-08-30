import type { SimulationRecord } from '../types/simulation';

export const simulationsMock: SimulationRecord[] = [
  {
    id: 'sim-demo-1',
    portfolioId: 'tech-growth',
    portfolioName: 'Tech Growth',
    mode: 'Historical Scenario',
    title: 'COVID-19 Market Shock',
    scenarioId: 'covid-19-shock-2020',
    createdAt: '2026-08-24T10:00:00.000Z',
    original: {
      cumulativeReturn: -28,
      annualizedVolatility: 34.2,
      maxDrawdown: -32.7,
      sharpeRatio: -0.82,
      endingValue: 7200
    }
  }
];

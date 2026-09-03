import React, { createContext, PropsWithChildren, useEffect, useMemo, useState } from 'react';
import type {
  DemoHolding as Holding,
  DemoPortfolio as Portfolio,
  DemoSimulationRecord as SimulationRecord
} from '../types/demo';
import {
  clearLocalAuraData,
  createEmptyPortfolio,
  loadActivePortfolioId,
  loadLearnProgress,
  loadPortfolios,
  loadSimulations,
  loadWatchlistSymbols,
  rebalanceByValue,
  saveActivePortfolioId,
  saveLearnProgress,
  savePortfolios,
  saveSimulations,
  saveWatchlistSymbols
} from './appStorage';
import {
  demoAllocationMetrics,
  demoScenarioMetrics,
  portfolioWithWeights
} from '../utils/localCalculations';
import { scenarioCatalog } from '../mocks/scenarios.mock';

// Temporary demo state for Dashboard, simulations, Assistant, and other
// screens that have not reached their API-integration phases. Production
// portfolios use PortfolioProvider; Analytics and Reports use ReportProvider.

type ContextValue = {
  loading: boolean;
  portfolios: Portfolio[];
  simulations: SimulationRecord[];
  activePortfolioId: string | null;
  activePortfolio: Portfolio | null;
  watchlistSymbols: string[];
  learnProgress: Record<string, boolean>;
  setActivePortfolio: (id: string) => Promise<void>;
  createPortfolio: (name: string) => Promise<Portfolio>;
  createPortfolioWithHoldings: (name: string, holdings: Holding[]) => Promise<Portfolio>;
  renamePortfolio: (id: string, name: string) => Promise<void>;
  duplicatePortfolio: (id: string) => Promise<Portfolio | null>;
  deletePortfolio: (id: string) => Promise<void>;
  addHolding: (portfolioId: string, holding: Holding) => Promise<void>;
  replaceHoldings: (portfolioId: string, holdings: Holding[]) => Promise<void>;
  runHistorical: (portfolioId: string, scenarioId: string) => Promise<SimulationRecord | null>;
  runAllocation: (portfolioId: string, weights: Record<string, number>) => Promise<SimulationRecord | null>;
  runCombined: (
    portfolioId: string,
    scenarioId: string,
    weights: Record<string, number>
  ) => Promise<SimulationRecord | null>;
  deleteSimulation: (id: string) => Promise<void>;
  addWatchlistSymbol: (symbol: string) => Promise<void>;
  removeWatchlistSymbol: (symbol: string) => Promise<void>;
  toggleLessonComplete: (lessonId: string) => Promise<void>;
  resetDemoData: () => Promise<void>;
};

export const AppDataContext = createContext<ContextValue | undefined>(undefined);

export function AppDataProvider({ children }: PropsWithChildren) {
  const [loading, setLoading] = useState(true);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [simulations, setSimulations] = useState<SimulationRecord[]>([]);
  const [activePortfolioId, setActivePortfolioId] = useState<string | null>(null);
  const [watchlistSymbols, setWatchlistSymbols] = useState<string[]>([]);
  const [learnProgress, setLearnProgress] = useState<Record<string, boolean>>({});

  useEffect(() => {
    (async () => {
      const [
        savedPortfolios,
        savedSimulations,
        savedActiveId,
        savedWatchlist,
        savedLearnProgress
      ] = await Promise.all([
        loadPortfolios(),
        loadSimulations(),
        loadActivePortfolioId(),
        loadWatchlistSymbols(),
        loadLearnProgress()
      ]);

      setPortfolios(savedPortfolios);
      setSimulations(savedSimulations);
      setWatchlistSymbols(savedWatchlist);
      setLearnProgress(savedLearnProgress);

      const firstId = savedPortfolios[0]?.id ?? null;
      setActivePortfolioId(
        savedActiveId && savedPortfolios.some((item) => item.id === savedActiveId)
          ? savedActiveId
          : firstId
      );
      setLoading(false);
    })();
  }, []);

  async function commitPortfolios(next: Portfolio[]) {
    setPortfolios(next);
    await savePortfolios(next);
  }

  async function setActivePortfolio(id: string) {
    setActivePortfolioId(id);
    await saveActivePortfolioId(id);
  }

  async function createPortfolio(name: string) {
    const portfolio = createEmptyPortfolio(name);
    await commitPortfolios([portfolio, ...portfolios]);
    await setActivePortfolio(portfolio.id);
    return portfolio;
  }

  async function createPortfolioWithHoldings(name: string, holdings: Holding[]) {
    const base = createEmptyPortfolio(name);
    const balanced = rebalanceByValue(holdings);
    const portfolio: Portfolio = {
      ...base,
      holdings: balanced,
      totalValue: balanced.reduce((sum, item) => sum + item.value, 0)
    };
    await commitPortfolios([portfolio, ...portfolios]);
    await setActivePortfolio(portfolio.id);
    return portfolio;
  }

  async function renamePortfolio(id: string, name: string) {
    const trimmed = name.trim();
    if (!trimmed) return;
    await commitPortfolios(
      portfolios.map((item) => (item.id === id ? { ...item, name: trimmed } : item))
    );
  }

  async function duplicatePortfolio(id: string) {
    const source = portfolios.find((item) => item.id === id);
    if (!source) return null;
    const copy: Portfolio = {
      ...source,
      id: `portfolio-${Date.now()}`,
      name: `${source.name} Copy`,
      holdings: source.holdings.map((holding) => ({ ...holding }))
    };
    await commitPortfolios([copy, ...portfolios]);
    await setActivePortfolio(copy.id);
    return copy;
  }

  async function deletePortfolio(id: string) {
    const next = portfolios.filter((item) => item.id !== id);
    await commitPortfolios(next);
    if (activePortfolioId === id) {
      const nextId = next[0]?.id ?? null;
      setActivePortfolioId(nextId);
      if (nextId) await saveActivePortfolioId(nextId);
    }
  }

  async function addHolding(portfolioId: string, holding: Holding) {
    const next = portfolios.map((portfolio) => {
      if (portfolio.id !== portfolioId) return portfolio;
      const withoutSameSymbol = portfolio.holdings.filter(
        (item) => item.symbol !== holding.symbol.toUpperCase()
      );
      const holdings = rebalanceByValue([
        ...withoutSameSymbol,
        { ...holding, symbol: holding.symbol.toUpperCase() }
      ]);
      const totalValue = holdings.reduce((sum, item) => sum + item.value, 0);
      return { ...portfolio, holdings, totalValue };
    });
    await commitPortfolios(next);
  }

  async function replaceHoldings(portfolioId: string, holdings: Holding[]) {
    const balanced = rebalanceByValue(holdings);
    const totalValue = balanced.reduce((sum, item) => sum + item.value, 0);
    await commitPortfolios(
      portfolios.map((portfolio) =>
        portfolio.id === portfolioId
          ? { ...portfolio, holdings: balanced, totalValue }
          : portfolio
      )
    );
  }

  async function runHistorical(portfolioId: string, scenarioId: string) {
    const portfolio = portfolios.find((item) => item.id === portfolioId);
    const scenario = scenarioCatalog.find((item) => item.id === scenarioId);
    if (!portfolio || !scenario) return null;

    const record: SimulationRecord = {
      id: `simulation-${Date.now()}`,
      portfolioId,
      portfolioName: portfolio.name,
      mode: 'Historical Scenario',
      title: scenario.name,
      scenarioId,
      createdAt: new Date().toISOString(),
      original: demoScenarioMetrics(portfolio, scenario)
    };

    const next = [record, ...simulations];
    setSimulations(next);
    await saveSimulations(next);
    return record;
  }

  async function runAllocation(portfolioId: string, weights: Record<string, number>) {
    const portfolio = portfolios.find((item) => item.id === portfolioId);
    if (!portfolio) return null;

    const originalWeights = Object.fromEntries(
      portfolio.holdings.map((holding) => [holding.symbol, holding.weight])
    );
    const original = demoAllocationMetrics(portfolio, originalWeights);
    const modified = demoAllocationMetrics(portfolio, weights);

    const record: SimulationRecord = {
      id: `simulation-${Date.now()}`,
      portfolioId,
      portfolioName: portfolio.name,
      mode: 'Allocation Change',
      title: 'Allocation Comparison',
      createdAt: new Date().toISOString(),
      original,
      modified,
      comparison: {
        returnDelta: Number((modified.cumulativeReturn - original.cumulativeReturn).toFixed(2)),
        volatilityDelta: Number(
          (modified.annualizedVolatility - original.annualizedVolatility).toFixed(2)
        ),
        drawdownDelta: Number((modified.maxDrawdown - original.maxDrawdown).toFixed(2))
      }
    };

    const next = [record, ...simulations];
    setSimulations(next);
    await saveSimulations(next);
    return record;
  }

  async function runCombined(
    portfolioId: string,
    scenarioId: string,
    weights: Record<string, number>
  ) {
    const portfolio = portfolios.find((item) => item.id === portfolioId);
    const scenario = scenarioCatalog.find((item) => item.id === scenarioId);
    if (!portfolio || !scenario) return null;

    const modifiedPortfolio = portfolioWithWeights(portfolio, weights);
    const original = demoScenarioMetrics(portfolio, scenario);
    const modified = demoScenarioMetrics(modifiedPortfolio, scenario);

    const record: SimulationRecord = {
      id: `simulation-${Date.now()}`,
      portfolioId,
      portfolioName: portfolio.name,
      mode: 'Combined',
      title: `${scenario.name} Comparison`,
      scenarioId,
      createdAt: new Date().toISOString(),
      original,
      modified,
      comparison: {
        returnDelta: Number((modified.cumulativeReturn - original.cumulativeReturn).toFixed(2)),
        volatilityDelta: Number(
          (modified.annualizedVolatility - original.annualizedVolatility).toFixed(2)
        ),
        drawdownDelta: Number((modified.maxDrawdown - original.maxDrawdown).toFixed(2))
      }
    };

    const next = [record, ...simulations];
    setSimulations(next);
    await saveSimulations(next);
    return record;
  }

  async function deleteSimulation(id: string) {
    const next = simulations.filter((item) => item.id !== id);
    setSimulations(next);
    await saveSimulations(next);
  }

  async function addWatchlistSymbol(symbol: string) {
    const normalized = symbol.trim().toUpperCase();
    if (!normalized || watchlistSymbols.includes(normalized)) return;
    const next = [...watchlistSymbols, normalized];
    setWatchlistSymbols(next);
    await saveWatchlistSymbols(next);
  }

  async function removeWatchlistSymbol(symbol: string) {
    const next = watchlistSymbols.filter((item) => item !== symbol);
    setWatchlistSymbols(next);
    await saveWatchlistSymbols(next);
  }

  async function toggleLessonComplete(lessonId: string) {
    const next = { ...learnProgress, [lessonId]: !learnProgress[lessonId] };
    setLearnProgress(next);
    await saveLearnProgress(next);
  }

  async function resetDemoData() {
    await clearLocalAuraData();

    const [defaults, defaultWatchlist] = await Promise.all([
      loadPortfolios(),
      loadWatchlistSymbols()
    ]);

    setPortfolios(defaults);
    setSimulations([]);
    setWatchlistSymbols(defaultWatchlist);
    setLearnProgress({});

    const firstId = defaults[0]?.id ?? null;
    setActivePortfolioId(firstId);
    if (firstId) await saveActivePortfolioId(firstId);
  }

  const activePortfolio =
    portfolios.find((item) => item.id === activePortfolioId) ?? portfolios[0] ?? null;

  const value = useMemo<ContextValue>(
    () => ({
      loading,
      portfolios,
      simulations,
      activePortfolioId,
      activePortfolio,
      watchlistSymbols,
      learnProgress,
      setActivePortfolio,
      createPortfolio,
      createPortfolioWithHoldings,
      renamePortfolio,
      duplicatePortfolio,
      deletePortfolio,
      addHolding,
      replaceHoldings,
      runHistorical,
      runAllocation,
      runCombined,
      deleteSimulation,
      addWatchlistSymbol,
      removeWatchlistSymbol,
      toggleLessonComplete,
      resetDemoData
    }),
    [
      loading,
      portfolios,
      simulations,
      activePortfolioId,
      watchlistSymbols,
      learnProgress
    ]
  );

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>;
}

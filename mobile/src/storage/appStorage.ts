import AsyncStorage from '@react-native-async-storage/async-storage';
import type { Portfolio, Holding } from '../types/portfolio';
import type { ReportSnapshot } from '../types/report';
import type { SimulationRecord } from '../types/simulation';
import { portfoliosMock } from '../mocks/portfolios.mock';

const PORTFOLIOS_KEY = 'aura_local_portfolios_v2';
const REPORTS_KEY = 'aura_local_reports_v2';
const SIMULATIONS_KEY = 'aura_local_simulations_v2';
const ACTIVE_PORTFOLIO_KEY = 'aura_active_portfolio_v2';
const WATCHLIST_KEY = 'aura_local_watchlist_v1';
const LEARN_PROGRESS_KEY = 'aura_learn_progress_v1';

export async function loadPortfolios(): Promise<Portfolio[]> {
  const raw = await AsyncStorage.getItem(PORTFOLIOS_KEY);
  if (raw) return JSON.parse(raw);
  await AsyncStorage.setItem(PORTFOLIOS_KEY, JSON.stringify(portfoliosMock));
  return portfoliosMock;
}

export async function savePortfolios(items: Portfolio[]) {
  await AsyncStorage.setItem(PORTFOLIOS_KEY, JSON.stringify(items));
}

export async function loadReports(): Promise<ReportSnapshot[]> {
  const raw = await AsyncStorage.getItem(REPORTS_KEY);
  return raw ? JSON.parse(raw) : [];
}

export async function saveReports(items: ReportSnapshot[]) {
  await AsyncStorage.setItem(REPORTS_KEY, JSON.stringify(items));
}

export async function loadSimulations(): Promise<SimulationRecord[]> {
  const raw = await AsyncStorage.getItem(SIMULATIONS_KEY);
  return raw ? JSON.parse(raw) : [];
}

export async function saveSimulations(items: SimulationRecord[]) {
  await AsyncStorage.setItem(SIMULATIONS_KEY, JSON.stringify(items));
}

export async function loadActivePortfolioId() {
  return AsyncStorage.getItem(ACTIVE_PORTFOLIO_KEY);
}

export async function saveActivePortfolioId(id: string) {
  await AsyncStorage.setItem(ACTIVE_PORTFOLIO_KEY, id);
}

export async function loadWatchlistSymbols(): Promise<string[]> {
  const raw = await AsyncStorage.getItem(WATCHLIST_KEY);
  if (raw) return JSON.parse(raw);
  const defaults = ['AAPL', 'NVDA', 'SPY', 'GLD', 'BTC-USD'];
  await AsyncStorage.setItem(WATCHLIST_KEY, JSON.stringify(defaults));
  return defaults;
}

export async function saveWatchlistSymbols(symbols: string[]) {
  await AsyncStorage.setItem(WATCHLIST_KEY, JSON.stringify(symbols));
}

export async function loadLearnProgress(): Promise<Record<string, boolean>> {
  const raw = await AsyncStorage.getItem(LEARN_PROGRESS_KEY);
  return raw ? JSON.parse(raw) : {};
}

export async function saveLearnProgress(progress: Record<string, boolean>) {
  await AsyncStorage.setItem(LEARN_PROGRESS_KEY, JSON.stringify(progress));
}

export function createEmptyPortfolio(name: string): Portfolio {
  return {
    id: `portfolio-${Date.now()}`,
    name: name.trim() || 'Untitled Portfolio',
    totalValue: 0,
    riskScore: 0,
    riskLevel: 'Low',
    annualizedReturn: 0,
    maxDrawdown: 0,
    holdings: []
  };
}

export function rebalanceByValue(holdings: Holding[]) {
  const total = holdings.reduce((sum, holding) => sum + holding.value, 0);
  if (!total) return holdings.map((holding) => ({ ...holding, weight: 0 }));
  return holdings.map((holding) => ({
    ...holding,
    weight: Number(((holding.value / total) * 100).toFixed(2))
  }));
}

export async function clearLocalAuraData() {
  await AsyncStorage.multiRemove([
    PORTFOLIOS_KEY,
    REPORTS_KEY,
    SIMULATIONS_KEY,
    ACTIVE_PORTFOLIO_KEY,
    WATCHLIST_KEY,
    LEARN_PROGRESS_KEY
  ]);
}

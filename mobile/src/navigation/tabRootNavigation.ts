import { CommonActions } from '@react-navigation/native';
import type { MainTabParamList } from './navigationTypes';

const STACK_ROOTS: Partial<Record<keyof MainTabParamList, string>> = {
  Portfolio: 'Portfolios',
  Simulate: 'Simulations',
  MoreTab: 'More'
};

// Only bottom-bar presses use this action; in-page links keep their exact context.
export function tabRootAction(tab: keyof MainTabParamList) {
  const root = STACK_ROOTS[tab];
  if (!root) return undefined; // Home and AI already render their main screen.

  return CommonActions.navigate(tab, {
    // Reset the selected child stack, even when a deep link was its first screen.
    state: { index: 0, routes: [{ name: root }] }
  });
}

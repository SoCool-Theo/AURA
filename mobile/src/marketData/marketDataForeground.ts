import { AppState } from 'react-native';
// Screen focus is owned by useFocusEffect; no background task or push.
export function watchMarketDataForeground(refresh: () => void, activity: (active: boolean) => void) {
  let interval: ReturnType<typeof setInterval> | undefined;
  let active = AppState.currentState === 'active';
  const start = () => { interval = setInterval(refresh, 300000); };
  activity(active);
  if (active) start();
  const subscription = AppState.addEventListener('change', value => {
    const next = value === 'active';
    if (next === active) return;
    active = next; activity(active);
    if (active) { start(); refresh(); }
    else { clearInterval(interval); interval = undefined; }
  });
  return () => { clearInterval(interval); subscription.remove(); };
}

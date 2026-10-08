import { AppState } from 'react-native';
// No background task, OS permission, push registration, or device token.
export function watchNotificationForeground(refresh: () => void) {
  const visibleRefresh = () => { if (AppState.currentState === 'active') refresh(); };
  const interval = setInterval(visibleRefresh, 30000);
  const subscription = AppState.addEventListener('change', visibleRefresh);
  return () => { clearInterval(interval); subscription.remove(); };
}

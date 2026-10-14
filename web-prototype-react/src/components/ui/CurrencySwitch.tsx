import type { CurrencyDisplayContext, DisplayCurrency } from '../../currencyDisplay';
import styles from './CurrencySwitch.module.css';

export function CurrencySwitch({ display, value, onChange, saved = false }: {
  display: CurrencyDisplayContext; value: DisplayCurrency; onChange: (value: DisplayCurrency) => void; saved?: boolean;
}) {
  return <div className={styles.control}>
    <div className={styles.options} role="group" aria-label="Display currency">
      {(['USD', 'THB'] as const).map(currency => <button type="button" key={currency}
        aria-pressed={value === currency} disabled={!display.views.some(view => view.currency === currency)}
        className={value === currency ? styles.selected : ''} onClick={() => onChange(currency)}>{currency}</button>)}
    </div>
    <p>{display.fx && display.views.length === 1 ? 'Currency conversion is unavailable for one or more displayed horizons.'
      : display.fx ? `${saved ? 'Saved ' : ''}USD/THB ${display.fx.rate} as of ${display.fx.as_of}. Display currency does not change allocation or risk.`
      : saved ? 'Currency conversion is unavailable because this simulation has no saved exchange rate.'
        : 'Currency conversion is unavailable because fresh USD/THB data is unavailable.'}</p>
  </div>;
}

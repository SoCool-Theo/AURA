import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Icon } from '../../../components/ui/Icon';
import styles from '../PortfolioIntegration.module.css';
import { supportedAssets } from '../supportedAssetSymbols';

type AssetSymbolFieldProps = {
  ariaLabel: string;
  disabled?: boolean;
  id: string;
  onChange: (value: string) => void;
  placeholder?: string;
  value: string;
};

export function AssetSymbolField({
  ariaLabel,
  disabled = false,
  id,
  onChange,
  placeholder = 'e.g. AAPL',
  value,
}: AssetSymbolFieldProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const pickerButtonRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const [pickerVisible, setPickerVisible] = useState(false);
  const titleId = `${id}-asset-picker-title`;
  const normalizedValue = value.trim().toUpperCase();

  useEffect(() => {
    if (!pickerVisible) return;
    closeButtonRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setPickerVisible(false);
        pickerButtonRef.current?.focus();
      }
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [pickerVisible]);

  useEffect(() => {
    if (disabled) setPickerVisible(false);
  }, [disabled]);

  function showSupportedAssets() {
    if (disabled) return;
    setPickerVisible(true);
  }

  function closePicker(restoreFocus = true) {
    setPickerVisible(false);
    if (restoreFocus) pickerButtonRef.current?.focus();
  }

  function chooseSymbol(symbol: string) {
    onChange(symbol);
    closePicker();
  }

  return (
    <div className={styles.assetSymbolField}>
      <input
        ref={inputRef}
        aria-label={ariaLabel}
        autoCapitalize="characters"
        autoComplete="off"
        disabled={disabled}
        onChange={event => onChange(event.target.value.toUpperCase())}
        placeholder={placeholder}
        value={value}
      />
      <button
        ref={pickerButtonRef}
        type="button"
        className={styles.assetSymbolPickerButton}
        aria-label="Choose a supported asset symbol"
        aria-expanded={pickerVisible}
        aria-haspopup="dialog"
        disabled={disabled}
        onClick={showSupportedAssets}
        title={`Choose from Aura's ${supportedAssets.length} supported assets`}
      >
        <Icon name="chevron-down" size={18} />
      </button>
      {pickerVisible && createPortal(
        <div className={styles.assetPickerOverlay}>
          <button
            type="button"
            className={styles.assetPickerBackdrop}
            aria-label="Close asset symbol picker"
            onClick={() => closePicker()}
          />
          <section
            className={styles.assetPickerDialog}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
          >
            <header className={styles.assetPickerHeader}>
              <div>
                <h2 id={titleId}>Choose asset symbol</h2>
                <p>Aura’s {supportedAssets.length} currently supported market-data symbols</p>
              </div>
              <button
                ref={closeButtonRef}
                type="button"
                className={styles.assetPickerClose}
                aria-label="Close asset symbol picker"
                onClick={() => closePicker()}
              >×</button>
            </header>
            <div className={styles.assetPickerOptions} role="radiogroup" aria-label="Supported asset symbols">
              {supportedAssets.map(asset => {
                const selected = asset.symbol === normalizedValue;
                return <button
                  type="button"
                  className={`${styles.assetPickerOption} ${selected ? styles.assetPickerOptionSelected : ''}`}
                  aria-checked={selected}
                  aria-label={`${asset.symbol}, ${asset.name}`}
                  key={asset.symbol}
                  onClick={() => chooseSymbol(asset.symbol)}
                  role="radio"
                >
                  <span className={styles.assetPickerOptionCopy}>
                    <strong>{asset.symbol}</strong>
                    <small>— {asset.name}</small>
                  </span>
                  {selected && <span aria-hidden="true">✓</span>}
                </button>;
              })}
            </div>
            <p className={styles.assetPickerNote}>You can close this list and type a symbol manually.</p>
          </section>
        </div>,
        document.body,
      )}
    </div>
  );
}

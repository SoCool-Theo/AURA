import { useEffect, useRef, useState, type InputHTMLAttributes } from 'react';
import { formatHoldingDecimalInput } from '../portfolioUi';

type HoldingDecimalInputProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'onChange' | 'type' | 'value'
> & {
  value: string;
  onValueChange: (value: string) => void;
};

const TWO_DECIMAL_INPUT = /^\d*(?:\.\d{0,2})?$/;

export function HoldingDecimalInput({
  value,
  onValueChange,
  onBlur,
  ...props
}: HoldingDecimalInputProps) {
  const [displayValue, setDisplayValue] = useState(() => formatHoldingDecimalInput(value));
  const edited = useRef(false);

  useEffect(() => {
    if (!edited.current) setDisplayValue(formatHoldingDecimalInput(value));
  }, [value]);

  return (
    <input
      {...props}
      inputMode="decimal"
      value={displayValue}
      onChange={event => {
        const nextValue = event.target.value;
        if (!TWO_DECIMAL_INPUT.test(nextValue)) return;
        edited.current = true;
        setDisplayValue(nextValue);
        onValueChange(nextValue);
      }}
      onBlur={event => {
        const formatted = formatHoldingDecimalInput(displayValue);
        setDisplayValue(formatted);
        if (edited.current && formatted !== value) onValueChange(formatted);
        edited.current = false;
        onBlur?.(event);
      }}
    />
  );
}

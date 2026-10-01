import React, { forwardRef, useEffect, useRef, useState } from 'react';
import type { TextInput, TextInputProps } from 'react-native';

import { formatHoldingDecimalInput } from '../../portfolio/portfolioFormatting';
import { Input } from '../ui/Input';

type HoldingDecimalInputProps = Omit<
  TextInputProps,
  'onChangeText' | 'value'
> & {
  error?: string | null;
  label: string;
  value: string;
  onValueChange: (value: string) => void;
};

const TWO_DECIMAL_INPUT = /^\d*(?:\.\d{0,2})?$/;

export const HoldingDecimalInput = forwardRef<TextInput, HoldingDecimalInputProps>(function HoldingDecimalInput({
  label,
  value,
  onValueChange,
  onBlur,
  ...props
}: HoldingDecimalInputProps, ref) {
  const [displayValue, setDisplayValue] = useState(() => formatHoldingDecimalInput(value));
  const edited = useRef(false);

  useEffect(() => {
    if (!edited.current) setDisplayValue(formatHoldingDecimalInput(value));
  }, [value]);

  return (
    <Input
      ref={ref}
      {...props}
      label={label}
      value={displayValue}
      keyboardType="decimal-pad"
      onChangeText={(nextValue) => {
        if (!TWO_DECIMAL_INPUT.test(nextValue)) return;
        edited.current = true;
        setDisplayValue(nextValue);
        onValueChange(nextValue);
      }}
      onBlur={(event) => {
        const formatted = formatHoldingDecimalInput(displayValue);
        setDisplayValue(formatted);
        if (edited.current && formatted !== value) onValueChange(formatted);
        edited.current = false;
        onBlur?.(event);
      }}
    />
  );
});

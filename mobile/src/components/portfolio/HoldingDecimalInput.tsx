import React, { forwardRef, useEffect, useRef, useState } from 'react';
import { usePortfolioPrivacy } from '../../privacy/PortfolioPrivacy';
import type { TextInput, TextInputProps } from 'react-native';
import { Text } from 'react-native';
import { colors } from '../../theme/theme';

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
  const { hideValues } = usePortfolioPrivacy();
  const [displayValue, setDisplayValue] = useState(() => formatHoldingDecimalInput(value));
  const edited = useRef(false);

  useEffect(() => {
    if (!edited.current) setDisplayValue(formatHoldingDecimalInput(value));
  }, [value]);

  return (<>
    <Input
      ref={ref}
      {...props}
      label={label}
      value={hideValues ? '' : displayValue}
      placeholder={hideValues ? '••••' : props.placeholder}
      editable={!hideValues && props.editable !== false}
      accessibilityHint={hideValues ? 'Turn off Hide portfolio values in Settings to edit.' : props.accessibilityHint}
      keyboardType="decimal-pad"
      onChangeText={(nextValue) => {
        if (hideValues) return;
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
    {hideValues ? <Text style={{ color: colors.muted, fontSize: 11 }}>Hidden. Turn off Hide portfolio values in Settings to edit.</Text> : null}
  </>);
});

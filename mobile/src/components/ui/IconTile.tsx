import React from 'react';
import { StyleSheet, View, type ColorValue } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../theme/colors';

type Tone = 'cyan' | 'purple' | 'blue' | 'green' | 'orange';

const tones: Record<Tone, { bg: ColorValue; fg: ColorValue }> = {
  cyan: { bg: colors.cyanBackground, fg: colors.primary },
  purple: { bg: colors.purpleBackground, fg: colors.purpleSoft },
  blue: { bg: colors.blueBackground, fg: colors.blue },
  green: { bg: colors.positiveBackground, fg: colors.success },
  orange: { bg: colors.warningBackground, fg: colors.warning }
};

export function IconTile({
  icon,
  tone = 'cyan',
  size = 48
}: {
  icon: keyof typeof Ionicons.glyphMap;
  tone?: Tone;
  size?: number;
}) {
  const selected = tones[tone];
  return (
    <View style={[styles.tile, {
      width: size,
      height: size,
      borderRadius: Math.round(size * 0.32),
      backgroundColor: selected.bg
    }]}>
      <Ionicons name={icon} size={Math.round(size * 0.46)} color={selected.fg} />
    </View>
  );
}

const styles = StyleSheet.create({
  tile: { alignItems: 'center', justifyContent: 'center' }
});

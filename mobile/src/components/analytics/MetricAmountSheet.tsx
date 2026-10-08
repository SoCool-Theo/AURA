import React from 'react';
import { usePrivateText, usePrivateValue } from '../../privacy/PortfolioPrivacy';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { colors, spacing } from '../../theme/theme';
import { Button } from '../ui/Button';

export type MetricAmountSheetContent = {
  title: string;
  percentage: string;
  amount: string;
  amountLabel: string;
  reference: string;
  explanation: string;
  tone: 'success' | 'danger';
};

export function MetricAmountSheet({
  content,
  onClose
}: {
  content: MetricAmountSheetContent | null;
  onClose: () => void;
}) {
  const toneColor = content?.tone === 'danger' ? colors.danger : colors.success;
  const privateValue = usePrivateValue();
  const privateText = usePrivateText();

  return (
    <Modal
      visible={content !== null}
      transparent
      animationType="slide"
      statusBarTranslucent
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <Pressable
          accessibilityLabel="Close metric details"
          accessibilityRole="button"
          style={StyleSheet.absoluteFill}
          onPress={onClose}
        />
        {content ? (
          <View accessibilityViewIsModal style={styles.sheet}>
            <View style={styles.handle} />
            <View style={styles.header}>
              <Text style={styles.title}>{content.title}</Text>
              <Pressable
                accessibilityLabel="Close metric details"
                accessibilityRole="button"
                hitSlop={10}
                onPress={onClose}
                style={styles.closeButton}
              >
                <Ionicons name="close" size={21} color={colors.text} />
              </Pressable>
            </View>

            <Text style={[styles.percentage, { color: toneColor }]}>
              {privateText(content.percentage)}
            </Text>
            <Text style={styles.amountLabel}>{content.amountLabel}</Text>
            <Text style={[styles.amount, { color: toneColor }]}>
              ≈ {privateValue(content.amount)}
            </Text>
            <View style={styles.explanationCard}>
              <Text style={styles.reference}>{privateText(content.reference)}</Text>
              <Text style={styles.explanation}>{privateText(content.explanation)}</Text>
            </View>
            <Button title="Close" onPress={onClose} />
          </View>
        ) : null}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0, 0, 0, 0.56)'
  },
  sheet: {
    gap: spacing.md,
    padding: spacing.xl,
    paddingBottom: spacing.xxxl,
    borderTopLeftRadius: 26,
    borderTopRightRadius: 26,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft
  },
  handle: {
    alignSelf: 'center',
    width: 42,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.border
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md
  },
  title: { color: colors.text, fontSize: 20, fontWeight: '900', flex: 1 },
  closeButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surfaceAlt
  },
  percentage: { fontSize: 34, fontWeight: '900' },
  amountLabel: { color: colors.textSecondary, fontSize: 12, fontWeight: '700' },
  amount: { fontSize: 25, fontWeight: '900' },
  explanationCard: {
    gap: spacing.sm,
    padding: spacing.lg,
    borderRadius: 16,
    backgroundColor: colors.surfaceAlt
  },
  reference: { color: colors.text, fontSize: 13, fontWeight: '800', lineHeight: 19 },
  explanation: { color: colors.textSecondary, fontSize: 12, lineHeight: 18 }
});

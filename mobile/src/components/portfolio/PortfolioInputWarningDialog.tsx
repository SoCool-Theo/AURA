import { Ionicons } from '@expo/vector-icons';
import React, { useEffect, useState } from 'react';
import { Modal, StyleSheet, Text, View } from 'react-native';

import {
  showPortfolioInputWarning,
  type PortfolioInputWarning
} from '../../portfolio/portfolioInputWarning';
import { colors, spacing } from '../../theme/theme';
import { Button } from '../ui/Button';

export function PortfolioInputWarningDialog({
  warning,
  revealField
}: {
  warning: PortfolioInputWarning | null;
  revealField: (fieldKey: string) => void;
}) {
  const [visible, setVisible] = useState(Boolean(warning));

  useEffect(() => {
    setVisible(Boolean(warning));
  }, [warning]);

  function revealInput() {
    if (!warning) return;
    setVisible(false);
    showPortfolioInputWarning(warning, revealField);
  }

  return (
    <Modal
      animationType="fade"
      onRequestClose={revealInput}
      statusBarTranslucent
      transparent
      visible={Boolean(warning) && visible}
    >
      <View style={styles.backdrop}>
        <View
          accessibilityLiveRegion="assertive"
          accessibilityViewIsModal
          style={styles.dialog}
        >
          <View style={styles.iconBox}>
            <Ionicons name="alert-circle-outline" color={colors.warning} size={26} />
          </View>
          <Text style={styles.overline}>INPUT NEEDS ATTENTION</Text>
          <Text style={styles.title}>Check your information</Text>
          <Text style={styles.message}>{warning?.message}</Text>
          <Button title="Show input" onPress={revealInput} style={styles.action} />
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
    backgroundColor: 'rgba(0,0,0,0.72)'
  },
  dialog: {
    width: '100%',
    maxWidth: 430,
    alignItems: 'center',
    padding: spacing.xl,
    borderWidth: 1,
    borderColor: colors.warning,
    borderRadius: 20,
    backgroundColor: colors.surface,
    shadowColor: '#000',
    shadowOpacity: 0.55,
    shadowRadius: 28,
    shadowOffset: { width: 0, height: 14 },
    elevation: 18
  },
  iconBox: {
    width: 50,
    height: 50,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
    borderRadius: 16,
    backgroundColor: colors.warningBackground
  },
  overline: {
    color: colors.warning,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 1.2
  },
  title: {
    marginTop: spacing.xs,
    color: colors.text,
    fontSize: 21,
    fontWeight: '900',
    textAlign: 'center'
  },
  message: {
    marginTop: spacing.md,
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 20,
    textAlign: 'center'
  },
  action: { minWidth: 160, marginTop: spacing.lg }
});

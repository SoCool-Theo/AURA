import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { StyleProp, StyleSheet, Text, View, ViewStyle } from 'react-native';

import {
  apiErrorPresentation,
  type ApiErrorPresentation
} from '../../api/apiErrorPresentation';
import { colors, spacing } from '../../theme/theme';
import { Button } from './Button';
import { Card } from './Card';

type ErrorActions = {
  onRetry?: () => void;
  onBack?: () => void;
  retryTitle?: string;
  backTitle?: string;
};

type ErrorContentProps = ErrorActions & {
  presentation: ApiErrorPresentation;
  compact?: boolean;
};

function ErrorContent({
  presentation,
  compact = false,
  onRetry,
  onBack,
  retryTitle = 'Try again',
  backTitle = 'Go back'
}: ErrorContentProps) {
  return (
    <>
      <View style={styles.heading}>
        <View style={[styles.iconBox, compact && styles.compactIconBox]}>
          <Ionicons name={presentation.icon} color={colors.danger} size={compact ? 18 : 24} />
        </View>
        <View style={styles.headingCopy}>
          <Text style={styles.code}>{presentation.code}</Text>
          <Text style={[styles.title, compact && styles.compactTitle]}>{presentation.title}</Text>
        </View>
      </View>
      <Text style={styles.message}>{presentation.message}</Text>
      {onRetry || onBack ? (
        <View style={[styles.actions, compact && styles.compactActions]}>
          {onRetry && presentation.retryable ? (
            <Button title={retryTitle} onPress={onRetry} style={styles.action} />
          ) : null}
          {onBack ? (
            <Button title={backTitle} variant="secondary" onPress={onBack} style={styles.action} />
          ) : null}
        </View>
      ) : null}
    </>
  );
}

export function ScreenErrorState({
  error,
  fallbackMessage,
  resourceName,
  message,
  ...actions
}: ErrorActions & {
  error: unknown;
  fallbackMessage?: string;
  resourceName?: string;
  message?: string;
}) {
  const presentation = apiErrorPresentation(error, {
    fallbackMessage,
    resourceName,
    message
  });
  return (
    <View style={styles.screen}>
      <Card style={styles.screenCard}>
        <ErrorContent presentation={presentation} {...actions} />
      </Card>
    </View>
  );
}

export function InlineErrorCard({
  error,
  fallbackMessage,
  resourceName,
  message,
  stale = false,
  style,
  ...actions
}: ErrorActions & {
  error: unknown;
  fallbackMessage?: string;
  resourceName?: string;
  message?: string;
  stale?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const presentation = apiErrorPresentation(error, {
    fallbackMessage,
    resourceName,
    message
  });
  return (
    <Card style={[styles.inlineCard, style]}>
      <ErrorContent presentation={presentation} compact {...actions} />
      {stale ? (
        <Text style={styles.stale}>Previously loaded information remains visible and may be out of date.</Text>
      ) : null}
    </Card>
  );
}

export function FormErrorSummary({
  error,
  message,
  title
}: {
  error: unknown;
  message?: string;
  title?: string;
}) {
  const classified: ApiErrorPresentation = error === null || error === undefined
    ? {
      code: 'FORM',
      title: 'Check your information',
      message: message ?? 'Review the form and try again.',
      icon: 'alert-circle-outline',
      retryable: false
    }
    : apiErrorPresentation(error, {
      fallbackMessage: 'Review the form and try again.',
      message
    });
  const presentation = title ? { ...classified, title } : classified;
  return (
    <Card style={styles.inlineCard}>
      <ErrorContent presentation={presentation} compact />
    </Card>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, justifyContent: 'center', padding: spacing.xl },
  screenCard: { gap: spacing.md, borderColor: colors.dangerBorder },
  inlineCard: { gap: spacing.sm, borderColor: colors.dangerBorder, marginTop: spacing.md },
  heading: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  headingCopy: { flex: 1 },
  iconBox: {
    width: 48,
    height: 48,
    borderRadius: 16,
    backgroundColor: colors.negativeBackground,
    alignItems: 'center',
    justifyContent: 'center'
  },
  compactIconBox: { width: 38, height: 38, borderRadius: 12 },
  code: { color: colors.danger, fontSize: 9, fontWeight: '900', letterSpacing: 1 },
  title: { color: colors.text, fontSize: 18, fontWeight: '900', marginTop: 2 },
  compactTitle: { fontSize: 15 },
  message: { color: colors.textSecondary, fontSize: 12, lineHeight: 19 },
  stale: { color: colors.warning, fontSize: 10, lineHeight: 16 },
  actions: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.sm },
  compactActions: { marginTop: spacing.xs },
  action: { flex: 1 }
});

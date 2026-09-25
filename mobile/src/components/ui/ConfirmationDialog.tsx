import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, spacing } from '../../theme/theme';
import { Button } from './Button';

type ConfirmationDialogProps = {
  visible: boolean;
  title: string;
  description: string;
  subject: string;
  subjectLabel: string;
  confirmLabel: string;
  busy: boolean;
  errorMessage?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
};

export function ConfirmationDialog({
  visible,
  title,
  description,
  subject,
  subjectLabel,
  confirmLabel,
  busy,
  errorMessage,
  onCancel,
  onConfirm,
}: ConfirmationDialogProps) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={() => { if (!busy) onCancel(); }}>
      <View style={styles.backdrop} accessibilityViewIsModal>
        <View style={styles.dialog}>
          <View style={styles.accent} />
          <View style={styles.content}>
            <View style={styles.header}>
              <View style={styles.titleRow}>
                <View style={styles.icon}><Ionicons name="trash-outline" color={colors.danger} size={21} /></View>
                <View style={styles.heading}>
                  <Text style={styles.title}>{title}</Text>
                  <Text style={styles.description}>{description}</Text>
                </View>
              </View>
              <Pressable accessibilityRole="button" accessibilityLabel={`Close ${title.toLowerCase()}`} accessibilityState={{ disabled: busy }} disabled={busy} onPress={onCancel} style={styles.close}>
                <Ionicons name="close" color={colors.text} size={20} />
              </Pressable>
            </View>
            <View style={styles.subject}>
              <Text style={styles.subjectLabel}>{subjectLabel}</Text>
              <Text style={styles.subjectValue}>{subject}</Text>
            </View>
            {errorMessage ? <Text accessibilityRole="alert" style={styles.error}>{errorMessage}</Text> : null}
            <View style={styles.actions}>
              <Button title="Cancel" variant="secondary" style={{ flex: 1 }} disabled={busy} onPress={onCancel} />
              <Button title={busy ? 'Working…' : confirmLabel} variant="danger" style={{ flex: 1 }} disabled={busy} onPress={onConfirm} />
            </View>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, justifyContent: 'center', padding: spacing.xl, backgroundColor: 'rgba(0,4,12,0.78)' },
  dialog: { overflow: 'hidden', borderWidth: 1, borderColor: colors.dangerBorder, borderRadius: 20, backgroundColor: colors.surface },
  accent: { height: 4, backgroundColor: colors.danger },
  content: { padding: spacing.lg },
  header: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: spacing.md },
  titleRow: { flex: 1, flexDirection: 'row', alignItems: 'flex-start', gap: spacing.md },
  icon: { width: 42, height: 42, borderRadius: 12, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.negativeBackground },
  heading: { flex: 1 },
  title: { color: colors.text, fontSize: 19, fontWeight: '900' },
  description: { marginTop: spacing.xs, color: colors.textSecondary, fontSize: 11, lineHeight: 17 },
  close: { width: 42, height: 42, borderRadius: 12, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surfaceAlt },
  subject: { marginTop: spacing.lg, padding: spacing.md, borderWidth: 1, borderColor: colors.dangerBorder, borderRadius: 12, backgroundColor: colors.negativeBackground },
  subjectLabel: { color: colors.muted, fontSize: 9, fontWeight: '900', letterSpacing: .8 },
  subjectValue: { marginTop: spacing.xs, color: colors.text, fontSize: 13, fontWeight: '900' },
  error: { marginTop: spacing.md, padding: spacing.sm, borderWidth: 1, borderColor: colors.dangerBorder, borderRadius: 10, backgroundColor: colors.negativeBackground, color: colors.danger, fontSize: 11, lineHeight: 17 },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md, marginTop: spacing.xl },
});

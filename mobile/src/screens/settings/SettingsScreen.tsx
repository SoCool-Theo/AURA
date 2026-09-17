import React, { useEffect, useRef, useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { useAuth } from '../../auth/useAuth';
import { useAppData } from '../../hooks/useAppData';
import { usePreferences } from '../../preferences/usePreferences';
import { colors, spacing } from '../../theme/theme';

export function SettingsScreen() {
  const { user, signOut } = useAuth();
  const { resetLocalData } = useAppData();
  const {
    themeMode,
    setThemeMode,
    storageError,
    displayName,
    setDisplayName,
    resetPreferences
  } = usePreferences();

  const resolvedName = displayName || 'Aura Investor';
  const [editingProfile, setEditingProfile] = useState(false);
  const [draftName, setDraftName] = useState(resolvedName);
  const [pending, setPending] = useState(false);
  const pendingRef = useRef(false);

  async function logout() {
    if (pendingRef.current) return;
    pendingRef.current = true;
    setPending(true);
    try { await signOut(); }
    catch { Alert.alert('Sign out incomplete', 'Aura could not remove the saved session. Please retry.'); }
    finally { pendingRef.current = false; setPending(false); }
  }

  useEffect(() => {
    setDraftName(resolvedName);
  }, [resolvedName]);

  function saveName() {
    const clean = draftName.trim();
    if (!clean) {
      Alert.alert('Name required', 'Enter a display name first.');
      return;
    }
    setDisplayName(clean);
    setEditingProfile(false);
  }

  function showHelp() {
    Alert.alert(
      'Help & Support',
      'In-app support messaging is not available yet. Please try again or contact the Aura team.'
    );
  }

  function showAbout() {
    Alert.alert(
      'About Aura',
      'Aura provides portfolio risk analytics, historical simulations, and AI explanations grounded in your saved results. Live quotes and Watchlist are unavailable.'
    );
  }

  function resetEverything() {
    if (pendingRef.current) return;
    Alert.alert(
      'Reset local app data?',
      'This resets Learn progress and preferences on this device, and removes obsolete demo storage. Your portfolios, reports, simulations, and session are not deleted.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: async () => {
            if (pendingRef.current) return;
            pendingRef.current = true;
            setPending(true);
            try {
              await resetLocalData();
              await resetPreferences();
            } catch {
              Alert.alert('Local reset incomplete', 'Some device data could not be reset. Please retry.');
            } finally {
              pendingRef.current = false;
              setPending(false);
            }
          }
        }
      ]
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content}>
        <PageTitle
          title="Settings"
          subtitle="Personalize Aura and manage local app data."
        />

        {storageError ? <Text style={styles.helper}>{storageError}</Text> : null}
        <Text style={styles.sectionTitle}>Profile</Text>
        <Card style={styles.profileCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {resolvedName.slice(0, 1).toUpperCase()}
            </Text>
          </View>

          <View style={{ flex: 1 }}>
            <Text style={styles.name}>{resolvedName}</Text>
            <Text style={styles.email}>{user?.email}</Text>
            <Text style={styles.helper}>
              Your display name is stored only on this device and is not part of your Aura account.
            </Text>
          </View>

          <Pressable
            accessibilityLabel="Edit local display name"
            accessibilityRole="button"
            style={styles.smallAction}
            onPress={() => setEditingProfile(true)}
          >
            <Ionicons name="pencil-outline" color={colors.primary} size={17} />
          </Pressable>
        </Card>

        <Text style={styles.sectionTitle}>Appearance</Text>
        <Card style={styles.appearanceCard}>
          <Text style={styles.settingTitle}>Color mode</Text>
          <Text style={styles.settingDescription}>
            Choose how Aura looks on this device.
          </Text>

          <View style={styles.themeRow}>
            <Pressable
              accessibilityLabel="Dark color mode"
              accessibilityRole="radio"
              accessibilityState={{ selected: themeMode === 'dark' }}
              onPress={() => setThemeMode('dark')}
              style={[
                styles.themeOption,
                themeMode === 'dark' && styles.themeSelected
              ]}
            >
              <View style={styles.themeIcon}>
                <Ionicons
                  name="moon-outline"
                  color={themeMode === 'dark' ? colors.primary : colors.muted}
                  size={21}
                />
              </View>
              <Text
                style={[
                  styles.themeLabel,
                  themeMode === 'dark' && styles.themeLabelSelected
                ]}
              >
                Dark
              </Text>
              {themeMode === 'dark' ? (
                <Ionicons
                  name="checkmark-circle"
                  color={colors.primary}
                  size={18}
                />
              ) : null}
            </Pressable>

            <Pressable
              accessibilityLabel="Light color mode"
              accessibilityRole="radio"
              accessibilityState={{ selected: themeMode === 'light' }}
              onPress={() => setThemeMode('light')}
              style={[
                styles.themeOption,
                themeMode === 'light' && styles.themeSelected
              ]}
            >
              <View style={styles.themeIcon}>
                <Ionicons
                  name="sunny-outline"
                  color={themeMode === 'light' ? colors.primary : colors.muted}
                  size={21}
                />
              </View>
              <Text
                style={[
                  styles.themeLabel,
                  themeMode === 'light' && styles.themeLabelSelected
                ]}
              >
                Light
              </Text>
              {themeMode === 'light' ? (
                <Ionicons
                  name="checkmark-circle"
                  color={colors.primary}
                  size={18}
                />
              ) : null}
            </Pressable>
          </View>
        </Card>

        <Text style={styles.sectionTitle}>Privacy & alerts</Text>
        <View style={styles.group}>
          <View style={[styles.row, styles.rowBorder]}>
            <View style={styles.rowIcon}>
              <Ionicons
                name="eye-off-outline"
                color={colors.textSecondary}
                size={20}
              />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.rowLabel}>Hide portfolio values</Text>
              <Text style={styles.rowDescription}>
                Unavailable: Aura does not currently provide monetary portfolio values.
              </Text>
            </View>
          </View>

          <View style={styles.row}>
            <View style={styles.rowIcon}>
              <Ionicons
                name="notifications-outline"
                color={colors.textSecondary}
                size={20}
              />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.rowLabel}>App notifications</Text>
              <Text style={styles.rowDescription}>
                Unavailable: notification delivery is not integrated.
              </Text>
            </View>
          </View>
        </View>

        <Text style={styles.sectionTitle}>Data & support</Text>
        <View style={styles.group}>
          <Pressable
            accessibilityLabel="Reset local data"
            accessibilityRole="button"
            accessibilityState={{ disabled: pending }}
            style={[styles.row, styles.rowBorder]}
            onPress={resetEverything}
            disabled={pending}
          >
            <View style={styles.rowIcon}>
              <Ionicons
                name="archive-outline"
                color={colors.textSecondary}
                size={20}
              />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.rowLabel}>Reset local data</Text>
              <Text style={styles.rowDescription}>
                Reset device preferences and Learn progress.
              </Text>
            </View>
            <Ionicons name="chevron-forward" color={colors.muted} size={18} />
          </Pressable>

          <Pressable
            accessibilityLabel="Help and support"
            accessibilityRole="button"
            style={[styles.row, styles.rowBorder]}
            onPress={showHelp}
          >
            <View style={styles.rowIcon}>
              <Ionicons
                name="help-circle-outline"
                color={colors.textSecondary}
                size={20}
              />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.rowLabel}>Help & Support</Text>
              <Text style={styles.rowDescription}>
                Setup and troubleshooting information.
              </Text>
            </View>
            <Ionicons name="chevron-forward" color={colors.muted} size={18} />
          </Pressable>

          <Pressable accessibilityLabel="About Aura" accessibilityRole="button" style={styles.row} onPress={showAbout}>
            <View style={styles.rowIcon}>
              <Ionicons
                name="information-circle-outline"
                color={colors.textSecondary}
                size={20}
              />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.rowLabel}>About Aura</Text>
              <Text style={styles.rowDescription}>
                Learn about Aura and its current features.
              </Text>
            </View>
            <Ionicons name="chevron-forward" color={colors.muted} size={18} />
          </Pressable>
        </View>

        <Button
          title={pending ? 'Please wait…' : 'Sign out'}
          variant="danger"
          onPress={() => void logout()}
          disabled={pending}
          style={{ marginTop: spacing.xl }}
        />
      </ScrollView>

      <Modal
        visible={editingProfile}
        transparent
        animationType="fade"
        onRequestClose={() => setEditingProfile(false)}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.modalAvoidingView}
        >
          <View style={styles.modalBackdrop}>
            <View style={styles.modalCard}>
              <View style={styles.modalHeader}>
                <View>
                  <Text style={styles.modalTitle}>Edit profile</Text>
                  <Text style={styles.modalSubtitle}>
                    Change your local Aura display name.
                  </Text>
                </View>
                <Pressable
                  accessibilityLabel="Close edit profile"
                  accessibilityRole="button"
                  style={styles.closeButton}
                  onPress={() => setEditingProfile(false)}
                >
                  <Ionicons name="close" color={colors.text} size={20} />
                </Pressable>
              </View>

              <Text style={styles.inputLabel}>Display name</Text>
              <TextInput
                accessibilityLabel="Display name"
                value={draftName}
                onChangeText={setDraftName}
                placeholder="Your name"
                placeholderTextColor={colors.muted}
                style={styles.input}
                autoCapitalize="words"
              />

              <View style={styles.modalActions}>
                <Button
                  title="Cancel"
                  variant="secondary"
                  style={{ flex: 1 }}
                  onPress={() => setEditingProfile(false)}
                />
                <Button
                  title="Save"
                  style={{ flex: 1 }}
                  onPress={saveName}
                />
              </View>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.background
  },
  content: {
    padding: spacing.lg,
    paddingBottom: 100
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '900',
    marginTop: spacing.xl,
    marginBottom: spacing.md
  },
  profileCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md
  },
  avatar: {
    width: 58,
    height: 58,
    borderRadius: 29,
    backgroundColor: colors.purpleBackground,
    alignItems: 'center',
    justifyContent: 'center'
  },
  avatarText: {
    color: colors.purpleSoft,
    fontSize: 23,
    fontWeight: '900'
  },
  name: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '900'
  },
  email: {
    color: colors.textSecondary,
    fontSize: 11,
    marginTop: 3
  },
  helper: {
    color: colors.muted,
    fontSize: 10,
    marginTop: 4,
    lineHeight: 15
  },
  smallAction: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: colors.surfaceAlt,
    alignItems: 'center',
    justifyContent: 'center'
  },
  appearanceCard: {
    gap: spacing.sm
  },
  settingTitle: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '900'
  },
  settingDescription: {
    color: colors.textSecondary,
    fontSize: 11,
    lineHeight: 17
  },
  themeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginTop: spacing.sm
  },
  themeOption: {
    flexGrow: 1,
    flexBasis: 130,
    minHeight: 86,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6
  },
  themeSelected: {
    borderColor: colors.primary
  },
  themeIcon: {
    width: 34,
    height: 34,
    borderRadius: 11,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surface
  },
  themeLabel: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: '800'
  },
  themeLabelSelected: {
    color: colors.primary
  },
  group: {
    backgroundColor: colors.surface,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    overflow: 'hidden'
  },
  row: {
    minHeight: 68,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md
  },
  rowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft
  },
  rowIcon: {
    width: 36,
    height: 36,
    borderRadius: 11,
    backgroundColor: colors.surfaceAlt,
    alignItems: 'center',
    justifyContent: 'center'
  },
  rowLabel: {
    color: colors.text,
    fontSize: 13,
    fontWeight: '800'
  },
  rowDescription: {
    color: colors.muted,
    fontSize: 10,
    lineHeight: 15,
    marginTop: 3
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent: 'center',
    padding: spacing.xl
  },
  modalAvoidingView: {
    flex: 1
  },
  modalCard: {
    backgroundColor: colors.surface,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing.md
  },
  modalTitle: {
    color: colors.text,
    fontSize: 19,
    fontWeight: '900'
  },
  modalSubtitle: {
    color: colors.textSecondary,
    fontSize: 11,
    marginTop: 4
  },
  closeButton: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: colors.surfaceAlt,
    alignItems: 'center',
    justifyContent: 'center'
  },
  inputLabel: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: '800',
    marginTop: spacing.xl,
    marginBottom: spacing.sm
  },
  input: {
    minHeight: 48,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
    color: colors.text,
    paddingHorizontal: spacing.md,
    fontSize: 14
  },
  modalActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginTop: spacing.xl
  }
});

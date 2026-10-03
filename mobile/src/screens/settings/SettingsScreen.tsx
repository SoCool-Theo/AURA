import React, { useEffect, useRef, useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '../../components/ui/Button';
import { ConfirmationDialog } from '../../components/ui/ConfirmationDialog';
import { DeleteAccountSection } from './DeleteAccountSection';
import { AboutAuraDialog } from './AboutAuraDialog';
import { Card } from '../../components/ui/Card';
import { PageTitle } from '../../components/ui/PageTitle';
import { authApi } from '../../api/authApi';
import { apiErrorPresentation, apiValidationIssues } from '../../api/apiErrorPresentation';
import { ApiError } from '../../api/apiClient';
import { accountDisplayName, accountInitials } from '../../auth/accountIdentity';
import { useAuth } from '../../auth/useAuth';
import { useAppData } from '../../hooks/useAppData';
import { usePreferences } from '../../preferences/usePreferences';
import { usePortfolioPrivacy } from '../../privacy/PortfolioPrivacy';
import { colors, spacing } from '../../theme/theme';
import type {
  AuthenticatedUserResponse,
  PreferredLanguage,
  ProfileTimezone,
  ProfileUpdateRequest
} from '../../types/auth';

type ProfileDraft = {
  displayName: string;
  email: string;
  phoneNumber: string;
  language: PreferredLanguage;
  timezone: ProfileTimezone;
  currentPassword: string;
};

function draftFromUser(user: AuthenticatedUserResponse | null): ProfileDraft {
  return {
    displayName: user?.display_name ?? '',
    email: user?.email ?? '',
    phoneNumber: user?.phone_number ?? '',
    language: user?.preferred_language ?? 'en',
    timezone: 'Asia/Bangkok',
    currentPassword: ''
  };
}

function profileRequestError(error: unknown, fallback: string): string {
  if (error instanceof ApiError && error.status === 403) {
    return 'The current password is incorrect.';
  }
  if (error instanceof ApiError && error.status === 409) {
    return 'That email address is already used by another Aura account.';
  }
  const issues = apiValidationIssues(error);
  if (issues.length) return issues.map((issue) => issue.message).join('. ');
  return apiErrorPresentation(error, { fallbackMessage: fallback }).message;
}

export function SettingsScreen() {
  const privacy = usePortfolioPrivacy();
  const { user, setCurrentUser, signOut } = useAuth();
  const { resetLocalData } = useAppData();
  const {
    themeMode,
    setThemeMode,
    storageError,
    resetPreferences
  } = usePreferences();

  const resolvedName = accountDisplayName(user);
  const initials = accountInitials(user);
  const [editingProfile, setEditingProfile] = useState(false);
  const [profileDraft, setProfileDraft] = useState<ProfileDraft>(() => draftFromUser(user));
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileNotice, setProfileNotice] = useState<string | null>(null);
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordDraft, setPasswordDraft] = useState({ current: '', next: '', confirm: '' });
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [accountDeleting, setAccountDeleting] = useState(false);
  const [showAboutAura, setShowAboutAura] = useState(false);
  const [confirmingSignOut, setConfirmingSignOut] = useState(false);
  const [signOutError, setSignOutError] = useState<string | null>(null);
  const signOutConfirmationRef = useRef(false);
  const pendingRef = useRef(false);

  async function logout() {
    if (!signOutConfirmationRef.current || pendingRef.current || accountDeleting) return;
    pendingRef.current = true;
    setPending(true);
    setSignOutError(null);
    try {
      await signOut();
      signOutConfirmationRef.current = false;
      setConfirmingSignOut(false);
    }
    catch { setSignOutError('Aura could not remove the saved session. Please retry sign out.'); }
    finally { pendingRef.current = false; setPending(false); }
  }

  function requestSignOut() {
    if (pendingRef.current || accountDeleting) return;
    signOutConfirmationRef.current = true;
    setSignOutError(null);
    setConfirmingSignOut(true);
  }

  function cancelSignOut() {
    if (pendingRef.current) return;
    signOutConfirmationRef.current = false;
    setConfirmingSignOut(false);
    setSignOutError(null);
  }

  useEffect(() => {
    setProfileDraft(draftFromUser(user));
  }, [user]);

  const emailChanged = Boolean(
    user && profileDraft.email.trim().toLowerCase() !== user.email
  );

  function openProfileEditor() {
    setProfileDraft(draftFromUser(user));
    setProfileError(null);
    setEditingProfile(true);
  }

  async function saveProfile() {
    if (!user || profileSaving) return;
    const displayName = profileDraft.displayName.trim() || null;
    const phoneNumber = profileDraft.phoneNumber.trim() || null;
    const email = profileDraft.email.trim().toLowerCase();
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setProfileError('Enter a valid email address.');
      return;
    }
    if (displayName && displayName.length > 100) {
      setProfileError('Display name must be 100 characters or fewer.');
      return;
    }
    if (phoneNumber && (
      phoneNumber.length < 4
      || phoneNumber.length > 32
      || !/^[+().\-\d\s]+$/.test(phoneNumber)
    )) {
      setProfileError('Phone number must be 4–32 characters and use only numbers, spaces, +, parentheses, periods, or hyphens.');
      return;
    }
    if (emailChanged && !profileDraft.currentPassword) {
      setProfileError('Enter your current password to change the account email.');
      return;
    }

    const request: ProfileUpdateRequest = {};
    if (displayName !== user.display_name) request.display_name = displayName;
    if (phoneNumber !== user.phone_number) request.phone_number = phoneNumber;
    if (profileDraft.language !== user.preferred_language) {
      request.preferred_language = profileDraft.language;
    }
    if (profileDraft.timezone !== user.timezone) request.timezone = profileDraft.timezone;
    if (email !== user.email) {
      request.email = email;
      request.current_password = profileDraft.currentPassword;
    }
    if (!Object.keys(request).length) {
      setEditingProfile(false);
      setProfileNotice('Your profile is already up to date.');
      return;
    }

    setProfileSaving(true);
    setProfileError(null);
    try {
      const updatedUser = await authApi.updateProfile(request);
      setCurrentUser(updatedUser);
      setProfileNotice('Profile changes saved.');
      setEditingProfile(false);
    } catch (error) {
      setProfileError(profileRequestError(error, 'Aura could not save your profile. Please try again.'));
    } finally {
      setProfileSaving(false);
    }
  }

  function openPasswordEditor() {
    setPasswordDraft({ current: '', next: '', confirm: '' });
    setPasswordError(null);
    setChangingPassword(true);
  }

  async function savePassword() {
    if (passwordSaving) return;
    if (!passwordDraft.current) {
      setPasswordError('Enter your current password.');
      return;
    }
    if (passwordDraft.next.length < 8) {
      setPasswordError('New password must be at least 8 characters.');
      return;
    }
    if (passwordDraft.current === passwordDraft.next) {
      setPasswordError('Choose a new password that differs from the current password.');
      return;
    }
    if (passwordDraft.next !== passwordDraft.confirm) {
      setPasswordError('New password and confirmation do not match.');
      return;
    }
    setPasswordSaving(true);
    setPasswordError(null);
    try {
      await authApi.changePassword({
        current_password: passwordDraft.current,
        new_password: passwordDraft.next
      });
      setPasswordDraft({ current: '', next: '', confirm: '' });
      setChangingPassword(false);
      setProfileNotice('Password changed successfully.');
    } catch (error) {
      setPasswordError(profileRequestError(error, 'Aura could not change your password. Please try again.'));
    } finally {
      setPasswordSaving(false);
    }
  }

  function showHelp() {
    Alert.alert(
      'Help & Support',
      'In-app support messaging is not available yet. Please try again or contact the Aura team.'
    );
  }

  function showAbout() {
    setShowAboutAura(true);
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
              {initials}
            </Text>
          </View>

          <View style={styles.profileIdentity}>
            <Text
              ellipsizeMode="middle"
              numberOfLines={user?.display_name ? 1 : 2}
              style={styles.name}
            >
              {resolvedName}
            </Text>
            {user?.display_name ? (
              <Text ellipsizeMode="middle" numberOfLines={1} style={styles.email}>
                {user.email}
              </Text>
            ) : null}
            <Text style={styles.helper}>
              {user?.phone_number || 'No phone number'} · {user?.preferred_language === 'th' ? 'Thai' : 'English'} · Bangkok
            </Text>
          </View>

          <Pressable
            accessibilityLabel="Edit account profile"
            accessibilityRole="button"
            style={styles.smallAction}
            onPress={openProfileEditor}
          >
            <Ionicons name="pencil-outline" color={colors.primary} size={17} />
          </Pressable>
        </Card>

        {profileNotice ? (
          <View accessibilityRole="alert" style={styles.profileNotice}>
            <Ionicons name="checkmark-circle-outline" color={colors.success} size={18} />
            <Text style={styles.profileNoticeText}>{profileNotice}</Text>
          </View>
        ) : null}

        <Pressable
          accessibilityLabel="Change account password"
          accessibilityRole="button"
          style={styles.securityAction}
          onPress={openPasswordEditor}
        >
          <View style={styles.rowIcon}>
            <Ionicons name="lock-closed-outline" color={colors.primary} size={20} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.rowLabel}>Change password</Text>
            <Text style={styles.rowDescription}>Verify your current password and choose a new one.</Text>
          </View>
          <Ionicons name="chevron-forward" color={colors.muted} size={18} />
        </Pressable>

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
                Hide personal amounts and share quantities. Remembered for this account on this device only.
              </Text>
            </View>
            <Switch accessibilityLabel="Hide portfolio values" value={privacy.hideValues}
              disabled={!privacy.ready} onValueChange={privacy.setHideValues}
              trackColor={{ false: colors.border, true: colors.primary }} thumbColor={colors.text} />
          </View>
          {privacy.storageError ? <Text accessibilityRole="alert" style={{ color: colors.danger, padding: spacing.md }}>{privacy.storageError}</Text> : null}

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

        <DeleteAccountSection disabled={pending || profileSaving || passwordSaving} onBusyChange={setAccountDeleting} />

        <Button
          title={pending ? 'Please wait…' : 'Sign out'}
          variant="danger"
          onPress={requestSignOut}
          disabled={pending || accountDeleting}
          style={{ marginTop: spacing.xl }}
        />
      </ScrollView>

      <AboutAuraDialog visible={showAboutAura} onClose={() => setShowAboutAura(false)} />

      <ConfirmationDialog visible={confirmingSignOut} title="Sign out?"
        description="You'll need to sign in again to access Aura. Your account, portfolios, reports, and saved simulations will not be deleted."
        subject={user?.email ?? resolvedName} subjectLabel="SIGNED-IN ACCOUNT" confirmLabel="Sign out"
        tone="danger" iconName="log-out-outline" busy={pending} errorMessage={signOutError}
        onCancel={cancelSignOut} onConfirm={() => void logout()} />

      <Modal
        visible={editingProfile}
        transparent
        animationType="fade"
        onRequestClose={() => { if (!profileSaving) setEditingProfile(false); }}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.modalAvoidingView}
        >
          <View style={styles.modalBackdrop}>
            <View style={styles.modalCard}>
              <View style={styles.modalHeader}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.modalTitle}>Edit profile</Text>
                  <Text style={styles.modalSubtitle}>
                    Changes are saved to your Aura account.
                  </Text>
                </View>
                <Pressable
                  accessibilityLabel="Close edit profile"
                  accessibilityRole="button"
                  style={styles.closeButton}
                  disabled={profileSaving}
                  onPress={() => setEditingProfile(false)}
                >
                  <Ionicons name="close" color={colors.text} size={20} />
                </Pressable>
              </View>
              <ScrollView
                keyboardShouldPersistTaps="handled"
                showsVerticalScrollIndicator={false}
                style={styles.modalScroll}
              >
                <Text style={styles.inputLabel}>Display name</Text>
                <TextInput
                  accessibilityLabel="Display name"
                  value={profileDraft.displayName}
                  onChangeText={(displayName) => setProfileDraft((current) => ({ ...current, displayName }))}
                  placeholder="Your name"
                  placeholderTextColor={colors.muted}
                  style={styles.input}
                  autoCapitalize="words"
                  maxLength={100}
                  editable={!profileSaving}
                />

                <Text style={styles.inputLabel}>Email address</Text>
                <TextInput
                  accessibilityLabel="Email address"
                  value={profileDraft.email}
                  onChangeText={(email) => setProfileDraft((current) => ({ ...current, email }))}
                  placeholder="name@example.com"
                  placeholderTextColor={colors.muted}
                  style={styles.input}
                  autoCapitalize="none"
                  keyboardType="email-address"
                  editable={!profileSaving}
                />

                <Text style={styles.inputLabel}>Phone number · Optional</Text>
                <TextInput
                  accessibilityLabel="Phone number"
                  value={profileDraft.phoneNumber}
                  onChangeText={(phoneNumber) => setProfileDraft((current) => ({ ...current, phoneNumber }))}
                  placeholder="+66 00 000 0000"
                  placeholderTextColor={colors.muted}
                  style={styles.input}
                  keyboardType="phone-pad"
                  maxLength={32}
                  editable={!profileSaving}
                />

                <Text style={styles.inputLabel}>Preferred language</Text>
                <View accessibilityRole="radiogroup" style={styles.choiceRow}>
                  {([
                    ['en', 'English'],
                    ['th', 'Thai']
                  ] as const).map(([value, label]) => (
                    <Pressable
                      key={value}
                      accessibilityRole="radio"
                      accessibilityState={{ selected: profileDraft.language === value }}
                      onPress={() => setProfileDraft((current) => ({ ...current, language: value }))}
                      style={[styles.choice, profileDraft.language === value && styles.choiceSelected]}
                    >
                      <Text style={[styles.choiceText, profileDraft.language === value && styles.choiceTextSelected]}>{label}</Text>
                    </Pressable>
                  ))}
                </View>

                <Text style={styles.inputLabel}>Timezone</Text>
                <View accessibilityLabel="Timezone UTC plus 7 Bangkok" style={[styles.choice, styles.choiceSelected]}>
                  <Text style={[styles.choiceText, styles.choiceTextSelected]}>UTC+07:00 Bangkok</Text>
                </View>

                {emailChanged ? (
                  <>
                    <Text style={styles.inputLabel}>Current password · Required for email change</Text>
                    <TextInput
                      accessibilityLabel="Current password for email change"
                      value={profileDraft.currentPassword}
                      onChangeText={(currentPassword) => setProfileDraft((current) => ({ ...current, currentPassword }))}
                      placeholder="Current password"
                      placeholderTextColor={colors.muted}
                      style={styles.input}
                      secureTextEntry
                      editable={!profileSaving}
                    />
                  </>
                ) : null}

                <Text style={styles.modalNote}>Language and timezone are stored now; translated copy and timezone-based formatting will be applied later.</Text>
                {profileError ? <Text accessibilityRole="alert" style={styles.modalError}>{profileError}</Text> : null}

                <View style={styles.modalActions}>
                  <Button
                    title="Cancel"
                    variant="secondary"
                    style={{ flex: 1 }}
                    disabled={profileSaving}
                    onPress={() => setEditingProfile(false)}
                  />
                  <Button
                    title={profileSaving ? 'Saving…' : 'Save profile'}
                    style={{ flex: 1 }}
                    disabled={profileSaving}
                    onPress={() => void saveProfile()}
                  />
                </View>
              </ScrollView>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      <Modal
        visible={changingPassword}
        transparent
        animationType="fade"
        onRequestClose={() => { if (!passwordSaving) setChangingPassword(false); }}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.modalAvoidingView}
        >
          <View style={styles.modalBackdrop}>
            <View style={styles.modalCard}>
              <View style={styles.modalHeader}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.modalTitle}>Change password</Text>
                  <Text style={styles.modalSubtitle}>Verify your current password before choosing a new one.</Text>
                </View>
                <Pressable
                  accessibilityLabel="Close change password"
                  accessibilityRole="button"
                  style={styles.closeButton}
                  disabled={passwordSaving}
                  onPress={() => setChangingPassword(false)}
                >
                  <Ionicons name="close" color={colors.text} size={20} />
                </Pressable>
              </View>

              <Text style={styles.inputLabel}>Current password</Text>
              <TextInput
                accessibilityLabel="Current password"
                value={passwordDraft.current}
                onChangeText={(current) => setPasswordDraft((value) => ({ ...value, current }))}
                placeholder="Current password"
                placeholderTextColor={colors.muted}
                style={styles.input}
                secureTextEntry
                editable={!passwordSaving}
              />
              <Text style={styles.inputLabel}>New password</Text>
              <TextInput
                accessibilityLabel="New password"
                value={passwordDraft.next}
                onChangeText={(next) => setPasswordDraft((value) => ({ ...value, next }))}
                placeholder="At least 8 characters"
                placeholderTextColor={colors.muted}
                style={styles.input}
                secureTextEntry
                editable={!passwordSaving}
              />
              <Text style={styles.inputLabel}>Confirm new password</Text>
              <TextInput
                accessibilityLabel="Confirm new password"
                value={passwordDraft.confirm}
                onChangeText={(confirm) => setPasswordDraft((value) => ({ ...value, confirm }))}
                placeholder="Repeat new password"
                placeholderTextColor={colors.muted}
                style={styles.input}
                secureTextEntry
                editable={!passwordSaving}
              />
              <Text style={styles.modalNote}>Use at least 8 characters. Aura never displays or returns your password.</Text>
              {passwordError ? <Text accessibilityRole="alert" style={styles.modalError}>{passwordError}</Text> : null}
              <View style={styles.modalActions}>
                <Button title="Cancel" variant="secondary" style={{ flex: 1 }} disabled={passwordSaving} onPress={() => setChangingPassword(false)} />
                <Button title={passwordSaving ? 'Changing…' : 'Change password'} style={{ flex: 1 }} disabled={passwordSaving} onPress={() => void savePassword()} />
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
    fontWeight: '900',
    lineHeight: 21,
    flexShrink: 1
  },
  profileIdentity: {
    flex: 1,
    minWidth: 0
  },
  email: {
    color: colors.textSecondary,
    fontSize: 11,
    marginTop: 3,
    flexShrink: 1
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
  profileNotice: {
    marginTop: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.successBorder,
    backgroundColor: colors.positiveBackground,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm
  },
  profileNoticeText: {
    flex: 1,
    color: colors.success,
    fontSize: 11,
    fontWeight: '700'
  },
  securityAction: {
    minHeight: 68,
    marginTop: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.surface,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md
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
  modalScroll: {
    maxHeight: 560
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
  choiceRow: {
    flexDirection: 'row',
    gap: spacing.sm
  },
  choiceColumn: {
    gap: spacing.sm
  },
  choice: {
    flexGrow: 1,
    minHeight: 44,
    paddingHorizontal: spacing.md,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
    alignItems: 'center',
    justifyContent: 'center'
  },
  choiceSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.selectedBackground
  },
  choiceText: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: '800'
  },
  choiceTextSelected: {
    color: colors.primary
  },
  modalNote: {
    marginTop: spacing.lg,
    color: colors.muted,
    fontSize: 10,
    lineHeight: 15
  },
  modalError: {
    marginTop: spacing.md,
    padding: spacing.md,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.dangerBorder,
    backgroundColor: colors.negativeBackground,
    color: colors.danger,
    fontSize: 11,
    lineHeight: 16
  },
  modalActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginTop: spacing.xl
  }
});

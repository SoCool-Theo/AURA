import React, { useRef, useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { AuthStackParamList } from '../../navigation/navigationTypes';
import { authenticationErrorMessage } from '../../auth/authErrors';
import { useAuth } from '../../auth/useAuth';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { colors, spacing } from '../../theme/theme';

type Props = NativeStackScreenProps<AuthStackParamList, 'Login'>;

const featureRows = [
  ['speedometer-outline', 'Portfolio Risk Intelligence'],
  ['pulse-outline', 'Historical What-If Simulations'],
  ['document-text-outline', 'Saved analysis reports']
] as const;

export function LoginScreen({ navigation }: Props) {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const submittingRef = useRef(false);

  async function submit() {
    if (submittingRef.current) return;

    const normalizedEmail = email.trim();
    if (!/^\S+@\S+\.\S+$/.test(normalizedEmail)) {
      Alert.alert('Check your email', 'Enter a valid email address.');
      return;
    }
    if (password.length < 8) {
      Alert.alert('Check your password', 'Password must contain at least 8 characters.');
      return;
    }

    submittingRef.current = true;
    try {
      setLoading(true);
      await signIn({ email: normalizedEmail, password });
      setPassword('');
    } catch (error) {
      Alert.alert(
        'Unable to sign in',
        authenticationErrorMessage(
          error,
          'Aura could not complete sign in. Please try again.'
        )
      );
    } finally {
      submittingRef.current = false;
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.brandRow}>
          <View style={styles.logo}><Text style={styles.logoText}>A</Text></View>
          <View><Text style={styles.brand}>Aura</Text><Text style={styles.brandMeta}>Portfolio Risk Intelligence</Text></View>
        </View>

        <View style={styles.hero}>
          <Text style={styles.eyebrow}>UNDERSTAND YOUR PORTFOLIO</Text>
          <Text style={styles.heroTitle}>Risk intelligence, explained simply.</Text>
          <Text style={styles.heroText}>Build portfolios, analyze risk, test historical scenarios, and keep every result organized in one investor workspace.</Text>
        </View>

        <View style={styles.features}>
          {featureRows.map(([icon, label]) => (
            <View key={label} style={styles.featureRow}>
              <View style={styles.featureIcon}><Ionicons name={icon} size={17} color={colors.primary} /></View>
              <Text style={styles.featureText}>{label}</Text>
            </View>
          ))}
        </View>

        <Card style={styles.formCard}>
          <Text style={styles.formTitle}>Welcome back</Text>
          <Text style={styles.formText}>Sign in to continue to your Aura dashboard.</Text>
          <View style={styles.form}>
            <Input label="Email" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" editable={!loading} />
            <Input label="Password" value={password} onChangeText={setPassword} secureTextEntry editable={!loading} />
            <Button title={loading ? 'Signing in…' : 'Sign in'} onPress={submit} disabled={loading} />
            <Button title="Create an account" variant="secondary" onPress={() => navigation.navigate('Register')} disabled={loading} />
          </View>
          <Text style={styles.note}>Your Aura session is stored securely on this device.</Text>
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { flexGrow: 1, padding: spacing.xl, paddingBottom: 50 },
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  logo: { width: 46, height: 46, borderRadius: 14, backgroundColor: colors.cyanBackground, borderWidth: 1, borderColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  logoText: { color: colors.primary, fontSize: 22, fontWeight: '900' },
  brand: { color: colors.text, fontSize: 20, fontWeight: '900' },
  brandMeta: { color: colors.muted, fontSize: 9, marginTop: 2, textTransform: 'uppercase', letterSpacing: 0.8 },
  hero: { marginTop: 42 },
  eyebrow: { color: colors.primary, fontSize: 9, fontWeight: '900', letterSpacing: 1.1 },
  heroTitle: { color: colors.text, fontSize: 31, lineHeight: 36, fontWeight: '900', marginTop: spacing.sm },
  heroText: { color: colors.textSecondary, fontSize: 13, lineHeight: 20, marginTop: spacing.md },
  features: { gap: spacing.sm, marginTop: spacing.xl },
  featureRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  featureIcon: { width: 34, height: 34, borderRadius: 11, backgroundColor: colors.surfaceAlt, alignItems: 'center', justifyContent: 'center' },
  featureText: { color: colors.textSecondary, fontSize: 11, fontWeight: '700' },
  formCard: { marginTop: 34 },
  formTitle: { color: colors.text, fontSize: 20, fontWeight: '900' },
  formText: { color: colors.textSecondary, fontSize: 11, marginTop: 4 },
  form: { gap: spacing.md, marginTop: spacing.xl },
  note: { color: colors.muted, fontSize: 9, lineHeight: 14, textAlign: 'center', marginTop: spacing.md }
});

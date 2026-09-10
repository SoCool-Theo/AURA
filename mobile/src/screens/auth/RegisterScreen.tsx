import React, { useRef, useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { AuthStackParamList } from '../../navigation/navigationTypes';
import { authenticationErrorMessage } from '../../auth/authErrors';
import { useAuth } from '../../auth/useAuth';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { colors, spacing } from '../../theme/theme';

type Props = NativeStackScreenProps<AuthStackParamList, 'Register'>;

export function RegisterScreen({ navigation }: Props) {
  const { register } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
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
    if (password !== confirmPassword) {
      Alert.alert('Check your passwords', 'Passwords do not match.');
      return;
    }

    submittingRef.current = true;
    try {
      setLoading(true);
      await register({ email: normalizedEmail, password });
      setPassword('');
      setConfirmPassword('');
      Alert.alert(
        'Account created',
        'Your Aura account is ready. Sign in with your email and password to continue.',
        [{ text: 'Continue to sign in', onPress: () => navigation.navigate('Login') }]
      );
    } catch (error) {
      Alert.alert(
        'Unable to register',
        authenticationErrorMessage(
          error,
          'Aura could not create the account. Please try again.'
        )
      );
    } finally {
      submittingRef.current = false;
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardAvoider}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardDismissMode="on-drag"
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.brand}><Text style={styles.brandMark}>A</Text><Text style={styles.brandName}>Aura</Text></View>
          <Text style={styles.title}>Create your Aura account</Text>
          <Text style={styles.subtitle}>Build portfolios, understand risk, and explore historical scenarios.</Text>

          <Card style={styles.formCard}>
            <View style={styles.form}>
              <Input label="Email" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" editable={!loading} />
              <Input label="Password" value={password} onChangeText={setPassword} secureTextEntry editable={!loading} />
              <Input label="Confirm password" value={confirmPassword} onChangeText={setConfirmPassword} secureTextEntry editable={!loading} />
              <Button title={loading ? 'Creating account…' : 'Create account'} onPress={submit} disabled={loading} />
              <Button title="Back to sign in" variant="secondary" onPress={() => navigation.navigate('Login')} disabled={loading} />
            </View>
          </Card>

          <Text style={styles.note}>Aura is educational portfolio-risk software and does not provide buy or sell advice.</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  keyboardAvoider: { flex: 1 },
  content: { flexGrow: 1, justifyContent: 'center', padding: spacing.xl },
  brand: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginBottom: spacing.xl },
  brandMark: { width: 36, height: 36, borderRadius: 11, backgroundColor: colors.cyanBackground, color: colors.primary, textAlign: 'center', textAlignVertical: 'center', fontSize: 18, fontWeight: '900' },
  brandName: { color: colors.text, fontSize: 19, fontWeight: '900' },
  title: { color: colors.text, fontSize: 29, lineHeight: 34, fontWeight: '900' },
  subtitle: { color: colors.textSecondary, lineHeight: 20, fontSize: 13, marginTop: spacing.sm },
  formCard: { marginTop: spacing.xl },
  form: { gap: spacing.md },
  note: { color: colors.muted, textAlign: 'center', fontSize: 10, lineHeight: 15, marginTop: spacing.xl }
});

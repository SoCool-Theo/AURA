import React, { useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { AuthStackParamList } from '../../navigation/navigationTypes';
import { useAuth } from '../../auth/useAuth';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { colors, spacing, typography } from '../../theme/theme';

type Props = NativeStackScreenProps<AuthStackParamList, 'Login'>;

export function LoginScreen({ navigation }: Props) {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('demo@aura.app');
  const [password, setPassword] = useState('password');
  const [loading, setLoading] = useState(false);

  async function submit() {
    try {
      setLoading(true);
      await signIn(email, password);
    } catch (error) {
      Alert.alert('Unable to sign in', error instanceof Error ? error.message : 'Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.mark}><Text style={styles.markText}>A</Text></View>
        <Text style={styles.title}>Aura</Text>
        <Text style={styles.subtitle}>Portfolio risk intelligence, explained simply.</Text>
        <View style={styles.form}>
          <Input label="Email" value={email} onChangeText={setEmail} keyboardType="email-address" />
          <Input label="Password" value={password} onChangeText={setPassword} secureTextEntry />
          <Button title={loading ? 'Signing in…' : 'Sign in'} onPress={submit} disabled={loading} />
          <Button title="Create an account" variant="secondary" onPress={() => navigation.navigate('Register')} />
        </View>
        <Text style={styles.note}>Mock mode is enabled by default, so the demo credentials work without the backend.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { flexGrow: 1, justifyContent: 'center', padding: spacing.lg, gap: spacing.md },
  mark: { width: 72, height: 72, borderRadius: 22, borderWidth: 1, borderColor: colors.primary, backgroundColor: colors.surfaceAlt, alignItems: 'center', justifyContent: 'center', alignSelf: 'center' },
  markText: { color: colors.primary, fontSize: 30, fontWeight: '900' },
  title: { color: colors.text, ...typography.h1, textAlign: 'center' },
  subtitle: { color: colors.textSecondary, textAlign: 'center', lineHeight: 21 },
  form: { gap: spacing.md, marginTop: spacing.xl },
  note: { color: colors.muted, textAlign: 'center', fontSize: 12, marginTop: spacing.md }
});

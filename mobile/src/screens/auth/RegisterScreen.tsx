import React, { useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { AuthStackParamList } from '../../navigation/navigationTypes';
import { useAuth } from '../../auth/useAuth';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { colors, spacing } from '../../theme/theme';

type Props = NativeStackScreenProps<AuthStackParamList, 'Register'>;

export function RegisterScreen({ navigation }: Props) {
  const { register } = useAuth();
  const [name, setName] = useState('Aura Investor');
  const [email, setEmail] = useState('new@aura.app');
  const [password, setPassword] = useState('password');
  const [loading, setLoading] = useState(false);

  async function submit() {
    try {
      setLoading(true);
      await register(name, email, password);
    } catch (error) {
      Alert.alert('Unable to register', error instanceof Error ? error.message : 'Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.brand}><Text style={styles.brandMark}>A</Text><Text style={styles.brandName}>Aura</Text></View>
        <Text style={styles.title}>Create your Aura account</Text>
        <Text style={styles.subtitle}>Build portfolios, understand risk, and explore historical scenarios.</Text>

        <Card style={styles.formCard}>
          <View style={styles.form}>
            <Input label="Name" value={name} onChangeText={setName} autoCapitalize="words" />
            <Input label="Email" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" />
            <Input label="Password" value={password} onChangeText={setPassword} secureTextEntry />
            <Button title={loading ? 'Creating account…' : 'Create account'} onPress={submit} disabled={loading} />
            <Button title="Back to sign in" variant="secondary" onPress={() => navigation.goBack()} />
          </View>
        </Card>

        <Text style={styles.note}>Aura is educational portfolio-risk software and does not provide buy or sell advice.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
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

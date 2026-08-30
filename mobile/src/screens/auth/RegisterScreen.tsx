import React, { useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { AuthStackParamList } from '../../navigation/navigationTypes';
import { useAuth } from '../../auth/useAuth';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { colors, spacing, typography } from '../../theme/theme';

type Props = NativeStackScreenProps<AuthStackParamList, 'Register'>;

export function RegisterScreen({ navigation }: Props) {
  const { register } = useAuth();
  const [name, setName] = useState('Aura Investor');
  const [email, setEmail] = useState('new@aura.app');
  const [password, setPassword] = useState('password');

  async function submit() {
    try {
      await register(name, email, password);
    } catch (error) {
      Alert.alert('Unable to register', error instanceof Error ? error.message : 'Please try again.');
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Create your Aura account</Text>
        <Text style={styles.subtitle}>Build portfolios, understand risk, and explore historical scenarios.</Text>
        <View style={styles.form}>
          <Input label="Name" value={name} onChangeText={setName} autoCapitalize="words" />
          <Input label="Email" value={email} onChangeText={setEmail} keyboardType="email-address" />
          <Input label="Password" value={password} onChangeText={setPassword} secureTextEntry />
          <Button title="Create account" onPress={submit} />
          <Button title="Back to sign in" variant="secondary" onPress={() => navigation.goBack()} />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { flexGrow: 1, justifyContent: 'center', padding: spacing.lg, gap: spacing.md },
  title: { color: colors.text, ...typography.h1 },
  subtitle: { color: colors.textSecondary, lineHeight: 21 },
  form: { gap: spacing.md, marginTop: spacing.xl }
});

import React, { useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { useAppData } from '../../hooks/useAppData';
import { colors, spacing, typography } from '../../theme/theme';

export function CreatePortfolioScreen({ navigation }: { navigation: any }) {
  const { createPortfolio } = useAppData();
  const [name, setName] = useState('');

  async function create() {
    if (!name.trim()) {
      Alert.alert('Portfolio name required', 'Enter a name before creating the portfolio.');
      return;
    }
    const portfolio = await createPortfolio(name);
    navigation.replace('PortfolioDetail', { portfolioId: portfolio.id });
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Create portfolio</Text>
        <Text style={styles.subtitle}>Start with a name, then add assets and invested amounts.</Text>
        <Input
          label="Portfolio name"
          placeholder="e.g. Long-Term Growth"
          value={name}
          onChangeText={setName}
          autoCapitalize="words"
        />
        <Button title="Create portfolio" onPress={create} style={{ marginTop: spacing.lg }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg },
  title: { color: colors.text, ...typography.h1 },
  subtitle: { color: colors.textSecondary, marginVertical: spacing.md, lineHeight: 20 }
});

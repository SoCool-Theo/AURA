import React, { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { useAppData } from '../../hooks/useAppData';
import { colors, spacing, typography } from '../../theme/theme';

const riskLevels = ['Low', 'Medium', 'High'] as const;

export function AddAssetScreen({ route, navigation }: { route: any; navigation: any }) {
  const { addHolding } = useAppData();
  const portfolioId = route.params.portfolioId;
  const [symbol, setSymbol] = useState('AAPL');
  const [name, setName] = useState('Apple Inc.');
  const [amount, setAmount] = useState('1000');
  const [risk, setRisk] = useState<typeof riskLevels[number]>('Medium');

  async function add() {
    const value = Number(amount);
    if (!symbol.trim() || !name.trim() || !Number.isFinite(value) || value <= 0) {
      Alert.alert('Check the asset', 'Enter a symbol, asset name and positive invested amount.');
      return;
    }
    await addHolding(portfolioId, {
      symbol: symbol.trim().toUpperCase(),
      name: name.trim(),
      value,
      weight: 0,
      risk
    });
    navigation.goBack();
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Add asset</Text>
        <Text style={styles.subtitle}>Weights are recalculated automatically from invested amounts.</Text>

        <Input label="Symbol" value={symbol} onChangeText={(value) => setSymbol(value.toUpperCase())} autoCapitalize="characters" />
        <Input label="Asset name" value={name} onChangeText={setName} autoCapitalize="words" />
        <Input label="Amount invested" value={amount} onChangeText={setAmount} keyboardType="decimal-pad" />

        <Text style={styles.label}>Demo risk profile</Text>
        <View style={styles.chips}>
          {riskLevels.map((level) => (
            <Pressable
              key={level}
              onPress={() => setRisk(level)}
              style={[styles.chip, risk === level && styles.chipSelected]}
            >
              <Text style={[styles.chipText, risk === level && styles.chipTextSelected]}>{level}</Text>
            </Pressable>
          ))}
        </View>

        <Text style={styles.note}>
          This risk selector is only for the local frontend demo. The real backend analytics will be authoritative later.
        </Text>

        <Button title="Add to portfolio" onPress={add} style={{ marginTop: spacing.xl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, gap: spacing.md },
  title: { color: colors.text, ...typography.h1 },
  subtitle: { color: colors.textSecondary, marginBottom: spacing.md, lineHeight: 20 },
  label: { color: colors.textSecondary, fontWeight: '800', marginTop: spacing.sm },
  chips: { flexDirection: 'row', gap: spacing.sm },
  chip: { flex: 1, minHeight: 44, borderRadius: 14, backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border, alignItems: 'center', justifyContent: 'center' },
  chipSelected: { borderColor: colors.primary, backgroundColor: colors.selectedBackground },
  chipText: { color: colors.textSecondary, fontWeight: '800' },
  chipTextSelected: { color: colors.primary },
  note: { color: colors.muted, fontSize: 12, lineHeight: 18 }
});

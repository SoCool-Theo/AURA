import React from 'react';
import { Pressable, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../theme/colors';

export function HomeHeaderButton({ navigation }: { navigation: any }) {
  return (
    <Pressable
      onPress={() => navigation.getParent()?.navigate('Home')}
      style={({ pressed }) => [styles.button, pressed && { opacity: 0.6 }]}
      accessibilityRole="button"
      accessibilityLabel="Go to Home"
    >
      <Ionicons name="home-outline" color={colors.primary} size={21} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: { paddingHorizontal: 8, paddingVertical: 6 }
});

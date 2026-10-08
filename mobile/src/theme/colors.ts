import {
  DynamicColorIOS,
  Platform,
  type ColorValue
} from 'react-native';

export const lightPalette = {
  background: '#F4F7FB',
  backgroundSoft: '#EEF3F9',
  surface: '#FFFFFF',
  surfaceAlt: '#F0F4FA',
  surfaceElevated: '#E7EEF7',
  border: '#CBD5E1',
  borderSoft: '#E2E8F0',
  tabBar: '#FFFFFF',
  primary: '#0FAFA8',
  primarySoft: '#0B8F89',
  cyan: '#0891B2',
  purple: '#7C3AED',
  purpleSoft: '#6D28D9',
  blue: '#2563EB',
  text: '#0F172A',
  textSecondary: '#475569',
  muted: '#64748B',
  success: '#15803D',
  warning: '#B45309',
  danger: '#DC2626',
  positiveBackground: '#DCFCE7',
  negativeBackground: '#FEE2E2',
  purpleBackground: '#EDE9FE',
  cyanBackground: '#CCFBF1',
  blueBackground: '#DBEAFE',
  warningBackground: '#FEF3C7',
  selectedBackground: '#DFF7F5',
  summaryBackground: '#ECFEFF',
  dangerBorder: '#FCA5A5',
  successBorder: '#86EFAC',
  trackOn: '#5EEAD4',
  onPrimary: '#032925'
};

export const darkPalette = {
  background: '#07111F',
  backgroundSoft: '#0A1526',
  surface: '#101A2C',
  surfaceAlt: '#14213A',
  surfaceElevated: '#18263F',
  border: '#233149',
  borderSoft: '#1A2940',
  tabBar: '#0B1628',
  primary: '#31D6CF',
  primarySoft: '#76E5E0',
  cyan: '#2EC5E6',
  purple: '#8B5CF6',
  purpleSoft: '#A78BFA',
  blue: '#4C8DFF',
  text: '#F7FAFF',
  textSecondary: '#A7B2C7',
  muted: '#6D7C96',
  success: '#33D18F',
  warning: '#F6C453',
  danger: '#FF6B7A',
  positiveBackground: '#0D2C27',
  negativeBackground: '#2C171E',
  purpleBackground: '#21163D',
  cyanBackground: '#0C2B35',
  blueBackground: '#12264A',
  warningBackground: '#312611',
  selectedBackground: '#0D2A2A',
  summaryBackground: '#0A1D25',
  dangerBorder: '#5B2631',
  successBorder: '#164C3D',
  trackOn: '#1B6963',
  onPrimary: '#031614'
};

function adaptive(light: string, dark: string): ColorValue {
  if (Platform.OS === 'ios') {
    return DynamicColorIOS({ light, dark });
  }

  return dark;
}

export const colors = {
  background: adaptive(lightPalette.background, darkPalette.background),
  backgroundSoft: adaptive(
    lightPalette.backgroundSoft,
    darkPalette.backgroundSoft
  ),
  surface: adaptive(lightPalette.surface, darkPalette.surface),
  surfaceAlt: adaptive(lightPalette.surfaceAlt, darkPalette.surfaceAlt),
  surfaceElevated: adaptive(
    lightPalette.surfaceElevated,
    darkPalette.surfaceElevated
  ),
  border: adaptive(lightPalette.border, darkPalette.border),
  borderSoft: adaptive(lightPalette.borderSoft, darkPalette.borderSoft),
  tabBar: adaptive(lightPalette.tabBar, darkPalette.tabBar),

  primary: adaptive(lightPalette.primary, darkPalette.primary),
  primarySoft: adaptive(lightPalette.primarySoft, darkPalette.primarySoft),
  cyan: adaptive(lightPalette.cyan, darkPalette.cyan),
  purple: adaptive(lightPalette.purple, darkPalette.purple),
  purpleSoft: adaptive(lightPalette.purpleSoft, darkPalette.purpleSoft),
  blue: adaptive(lightPalette.blue, darkPalette.blue),

  text: adaptive(lightPalette.text, darkPalette.text),
  textSecondary: adaptive(
    lightPalette.textSecondary,
    darkPalette.textSecondary
  ),
  muted: adaptive(lightPalette.muted, darkPalette.muted),

  success: adaptive(lightPalette.success, darkPalette.success),
  warning: adaptive(lightPalette.warning, darkPalette.warning),
  danger: adaptive(lightPalette.danger, darkPalette.danger),

  positiveBackground: adaptive(
    lightPalette.positiveBackground,
    darkPalette.positiveBackground
  ),
  negativeBackground: adaptive(
    lightPalette.negativeBackground,
    darkPalette.negativeBackground
  ),
  purpleBackground: adaptive(
    lightPalette.purpleBackground,
    darkPalette.purpleBackground
  ),
  cyanBackground: adaptive(
    lightPalette.cyanBackground,
    darkPalette.cyanBackground
  ),
  blueBackground: adaptive(
    lightPalette.blueBackground,
    darkPalette.blueBackground
  ),
  warningBackground: adaptive(
    lightPalette.warningBackground,
    darkPalette.warningBackground
  ),
  selectedBackground: adaptive(
    lightPalette.selectedBackground,
    darkPalette.selectedBackground
  ),
  summaryBackground: adaptive(
    lightPalette.summaryBackground,
    darkPalette.summaryBackground
  ),
  dangerBorder: adaptive(lightPalette.dangerBorder, darkPalette.dangerBorder),
  successBorder: adaptive(lightPalette.successBorder, darkPalette.successBorder),
  trackOn: adaptive(lightPalette.trackOn, darkPalette.trackOn),
  onPrimary: adaptive(lightPalette.onPrimary, darkPalette.onPrimary)
};

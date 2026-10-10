# Aura Mobile Settings + Theme v5

This update makes Settings interactive instead of presenting dead rows.

## Working Settings

- Edit local display name
  - persists locally
  - updates the Home greeting
- Dark mode
  - persists locally
  - updates navigation, status bar and adaptive UI colors
- Light mode
  - persists locally
  - updates navigation, status bar and adaptive UI colors
- Hide portfolio values
  - persists locally
  - masks money values on Home, Portfolios and Portfolio Detail
- App notifications preference
  - persists locally for future backend notification integration
- Reset local data
  - restores demo portfolios/reports/simulations/watchlist/learn progress
  - resets preferences
- Help & Support
  - opens help information
- About Aura
  - opens product information
- Sign out
  - uses the existing authentication flow

## Theme implementation

iOS uses React Native `DynamicColorIOS` plus `Appearance.setColorScheme`, which allows existing StyleSheet-based screens to respond to the selected Light/Dark mode.

Android uses adaptive native platform colors for major background/surface/text tokens where possible, while preserving Aura's accent colors.

The backend is not required for these Settings features.

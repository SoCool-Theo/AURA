# Aura Mobile UI v4 – Exact Design Correction

This patch fixes the two issues visible in the previous premium UI build.

## Home

The Home page now follows the earlier Aura mobile design more literally:

1. Greeting
2. Active portfolio value + compact risk score ring
3. Annual return + volatility cards
4. Main risk driver
5. Four primary actions:
   - Analyze
   - Simulate
   - Ask Aura
   - Add Asset
6. Small Learn shortcut

The large performance graph and the four count-based dashboard boxes were removed from Home so the page stays concise.

## Analytics

The heatmap was removed.

It is replaced with **Asset Relationship / Correlation Pair Bars**:

- asset pair name
- correlation coefficient
- horizontal strength bar
- clear text label such as Strong positive / Moderate positive / Negative
- explanatory diversification text

The current values are explicitly marked as demo preview values. When FastAPI integration is enabled, these should be replaced with actual backend correlation values.

## Risk gauge

The gauge now accepts a real `size` prop. It no longer uses clipping/scaling containers, which caused the broken-looking ring on the previous Home screen.

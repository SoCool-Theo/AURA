import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type {
  PortfolioCurrency,
  PortfolioHoldingResponse,
  PortfolioPlannedPreviewHoldingResponse,
  PortfolioHoldingValuationResponse
} from '../../types/portfolio';
import { isPlannedPortfolioHolding, isRealPortfolioHolding } from '../../types/portfolio';
import { colors, spacing } from '../../theme/theme';
import { decimalWeightToPercent } from '../../portfolio/portfolioValidation';
import {
  formatCurrentAllocation,
  formatPortfolioMoney,
  formatPortfolioQuantity
} from '../../portfolio/portfolioFormatting';

export function AssetRow({
  holding,
  valuation,
  plannedPreview,
  valuationCurrency = 'USD'
}: {
  holding: PortfolioHoldingResponse;
  valuation?: PortfolioHoldingValuationResponse;
  plannedPreview?: PortfolioPlannedPreviewHoldingResponse;
  valuationCurrency?: PortfolioCurrency;
}) {
  const isReal = isRealPortfolioHolding(holding);
  const isPlanned = isPlannedPortfolioHolding(holding);
  return (
    <View style={styles.row}>
      <View style={styles.symbolBox}>
        <Text style={styles.symbol}>{holding.symbol.slice(0, 4)}</Text>
      </View>
      <View style={styles.middle}>
        <Text style={styles.name}>{holding.symbol}</Text>
        <Text style={styles.meta}>
          {isReal
            ? holding.purchase_date
              ? `${formatPortfolioQuantity(holding.shares)} owned · Purchased ${holding.purchase_date}`
              : `${formatPortfolioQuantity(holding.shares)} owned`
            : isPlanned
              ? `Proposed ${formatPortfolioMoney(holding.proposed_amount, valuationCurrency)}`
            : `Position ${holding.position + 1} · Legacy allocation`}
        </Text>
        {isReal && holding.invested_amount && holding.invested_currency ? (
          <Text style={styles.fact}>
            Invested {formatPortfolioMoney(
              holding.invested_amount,
              holding.invested_currency
            )}
          </Text>
        ) : isPlanned && plannedPreview ? (
          <Text style={styles.fact}>
            {plannedPreview.estimate_status === 'AVAILABLE'
              ? `Estimated ${formatPortfolioQuantity(plannedPreview.estimated_shares!)} shares · display only`
              : plannedPreview.estimate_status === 'FX_UNAVAILABLE'
                ? 'Share estimate unavailable: FX data missing'
                : 'Share estimate unavailable: price data missing'}
          </Text>
        ) : null}
      </View>
      <View style={styles.valueColumn}>
        <Text style={styles.weight}>
          {valuation
            ? formatPortfolioMoney(valuation.current_value, valuationCurrency)
            : plannedPreview
              ? `${decimalWeightToPercent(Number(plannedPreview.target_allocation)).toFixed(2)}%`
              : holding.weight === null
                ? 'Unavailable'
                : `${decimalWeightToPercent(holding.weight).toFixed(2)}%`}
        </Text>
        {valuation ? (
          <Text style={styles.allocation}>
            {formatCurrentAllocation(valuation.current_allocation)}
          </Text>
        ) : plannedPreview ? <Text style={styles.allocation}>Target allocation</Text> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, paddingVertical: 12 },
  symbolBox: {
    width: 44, height: 44, borderRadius: 14, backgroundColor: colors.surfaceAlt,
    alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: colors.border
  },
  symbol: { color: colors.primary, fontWeight: '900', fontSize: 11 },
  middle: { flex: 1 },
  name: { color: colors.text, fontWeight: '800' },
  meta: { color: colors.muted, marginTop: 4, fontSize: 12 },
  fact: { color: colors.textSecondary, marginTop: 3, fontSize: 10 },
  valueColumn: { alignItems: 'flex-end', maxWidth: 120 },
  weight: { color: colors.primary, fontSize: 13, fontWeight: '900' },
  allocation: { color: colors.textSecondary, fontSize: 10, marginTop: 4 }
});

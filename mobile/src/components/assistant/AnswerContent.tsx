import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import {
  formatAgentAnswer,
  type AnswerInlinePart
} from '../../agent/answerFormatting';
import { colors, spacing } from '../../theme/theme';

function FormattedText({
  parts,
  style
}: {
  parts: AnswerInlinePart[];
  style: object;
}) {
  return (
    <Text selectable style={style}>
      {parts.map((part, index) => (
        <Text
          key={`${part.text}-${index}`}
          style={part.bold ? styles.bold : undefined}
        >
          {part.text}
        </Text>
      ))}
    </Text>
  );
}

export function AnswerContent({ answer }: { answer: string }) {
  return (
    <View style={styles.content}>
      {formatAgentAnswer(answer).map((block, blockIndex) => {
        if (block.type === 'heading') {
          return (
            <FormattedText
              key={`heading-${blockIndex}`}
              parts={block.parts}
              style={styles.heading}
            />
          );
        }
        if (block.type === 'paragraph') {
          return (
            <FormattedText
              key={`paragraph-${blockIndex}`}
              parts={block.parts}
              style={styles.paragraph}
            />
          );
        }
        if (block.type === 'table') {
          return <View key={`table-${blockIndex}`} style={styles.tableFrame}>
            <Text style={styles.tableHint}>Swipe horizontally to view all columns.</Text>
            <ScrollView horizontal style={styles.tableScroll} accessibilityLabel="Aura answer table"
              showsHorizontalScrollIndicator>
              <View style={styles.table}>
                <View style={[styles.tableRow, styles.tableHeader]}>
                  {block.headers.map((parts, column) => <View key={column} style={styles.tableCell} accessibilityRole="header" accessible
                    accessibilityLabel={parts.map(part => part.text).join('')}>
                    <FormattedText parts={parts} style={{ ...styles.tableHeaderText, textAlign: block.alignments[column] }} />
                  </View>)}
                </View>
                {block.rows.map((row, rowIndex) => <View key={rowIndex} style={styles.tableRow}>
                  {row.map((parts, column) => <View key={column} style={styles.tableCell} accessible
                    accessibilityLabel={`${block.headers[column].map(part => part.text).join('')}: ${parts.map(part => part.text).join('')}`}>
                    <FormattedText parts={parts} style={{ ...styles.paragraph, textAlign: block.alignments[column] }} />
                  </View>)}
                </View>)}
              </View>
            </ScrollView>
          </View>;
        }
        return (
          <View key={`bullets-${blockIndex}`} style={styles.bulletList}>
            {block.items.map((parts, itemIndex) => (
              <View key={`bullet-${itemIndex}`} style={styles.bulletRow}>
                <Text style={styles.bullet}>•</Text>
                <FormattedText parts={parts} style={styles.bulletText} />
              </View>
            ))}
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  content: { gap: spacing.md },
  tableFrame: { minWidth: 0, gap: spacing.sm },
  tableHint: { color: colors.muted, fontSize: 11, lineHeight: 17 },
  tableScroll: { width: '100%', borderWidth: 1, borderColor: colors.border, borderRadius: 10 },
  table: { backgroundColor: colors.surface },
  tableRow: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  tableHeader: { backgroundColor: colors.surfaceAlt },
  tableCell: { width: 180, padding: spacing.md },
  tableHeaderText: { color: colors.primary, fontSize: 13, lineHeight: 22, fontWeight: '900' },
  heading: { color: colors.text, fontSize: 15, fontWeight: '900', lineHeight: 21 },
  paragraph: { color: colors.textSecondary, fontSize: 13, lineHeight: 22 },
  bold: { color: colors.text, fontWeight: '900' },
  bulletList: { gap: spacing.sm },
  bulletRow: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.sm },
  bullet: { color: colors.primary, fontSize: 16, lineHeight: 22 },
  bulletText: { flex: 1, color: colors.textSecondary, fontSize: 13, lineHeight: 22 }
});

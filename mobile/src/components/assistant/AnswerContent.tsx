import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

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
  heading: { color: colors.text, fontSize: 15, fontWeight: '900', lineHeight: 21 },
  paragraph: { color: colors.textSecondary, fontSize: 13, lineHeight: 22 },
  bold: { color: colors.text, fontWeight: '900' },
  bulletList: { gap: spacing.sm },
  bulletRow: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.sm },
  bullet: { color: colors.primary, fontSize: 16, lineHeight: 22 },
  bulletText: { flex: 1, color: colors.textSecondary, fontSize: 13, lineHeight: 22 }
});

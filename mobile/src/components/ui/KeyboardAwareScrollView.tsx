import React, { useCallback, useEffect, useRef } from 'react';
import {
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
  type ScrollViewProps,
  StyleSheet,
  TextInput
} from 'react-native';

export function KeyboardAwareScrollView({
  keyboardDismissMode = 'on-drag',
  keyboardShouldPersistTaps = 'handled',
  onFocus,
  onScroll,
  scrollEventThrottle = 16,
  ...props
}: ScrollViewProps) {
  const scrollViewRef = useRef<ScrollView>(null);
  const focusTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scrollOffsetRef = useRef(0);

  const revealFocusedInput = useCallback(() => {
    if (focusTimerRef.current) clearTimeout(focusTimerRef.current);

    focusTimerRef.current = setTimeout(() => {
      focusTimerRef.current = null;
      const focusedInput = TextInput.State.currentlyFocusedInput();
      const scrollView = scrollViewRef.current;
      if (!focusedInput || !scrollView) return;
      const nativeScrollView = scrollView.getNativeScrollRef();
      if (!nativeScrollView) return;

      nativeScrollView.measureInWindow((_scrollX, scrollY, _width, height) => {
        focusedInput.measureInWindow((_inputX, inputY, _inputWidth, inputHeight) => {
          const keyboardTop = Keyboard.metrics()?.screenY;
          const visibleTop = scrollY + 12;
          const visibleBottom = Math.min(
            scrollY + height,
            keyboardTop ?? Number.POSITIVE_INFINITY
          ) - 24;
          const inputBottom = inputY + inputHeight;
          const delta = inputBottom > visibleBottom
            ? inputBottom - visibleBottom
            : inputY < visibleTop
              ? inputY - visibleTop
              : 0;

          if (Math.abs(delta) < 1) return;
          scrollView.scrollTo({
            y: Math.max(0, scrollOffsetRef.current + delta),
            animated: true
          });
        });
      });
    }, 100);
  }, []);

  const handleScroll = useCallback((event: NativeSyntheticEvent<NativeScrollEvent>) => {
    scrollOffsetRef.current = event.nativeEvent.contentOffset.y;
    onScroll?.(event);
  }, [onScroll]);

  useEffect(() => {
    const subscription = Keyboard.addListener(
      Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow',
      revealFocusedInput
    );

    return () => {
      subscription.remove();
      if (focusTimerRef.current) clearTimeout(focusTimerRef.current);
    };
  }, [revealFocusedInput]);

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView
        ref={scrollViewRef}
        keyboardDismissMode={keyboardDismissMode}
        keyboardShouldPersistTaps={keyboardShouldPersistTaps}
        onScroll={handleScroll}
        scrollEventThrottle={scrollEventThrottle}
        onFocus={(event) => {
          onFocus?.(event);
          revealFocusedInput();
        }}
        {...props}
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 }
});

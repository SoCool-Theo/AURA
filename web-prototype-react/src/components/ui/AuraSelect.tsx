import { createPortal } from 'react-dom';
import { useEffect, useId, useRef, useState } from 'react';
import type { CSSProperties, KeyboardEvent } from 'react';
import { Icon } from './Icon';

export type AuraSelectTone = 'teal' | 'green' | 'amber' | 'red' | 'blue' | 'neutral';

export type AuraSelectOption<T extends string = string> = {
  value: T;
  label: string;
  description?: string;
  icon?: string;
  tone?: AuraSelectTone;
  disabled?: boolean;
};

interface AuraSelectProps<T extends string> {
  value: T;
  options: ReadonlyArray<AuraSelectOption<T>>;
  onChange: (value: T) => void;
  ariaLabel: string;
  className?: string;
  disabled?: boolean;
}

export function AuraSelect<T extends string>({
  value,
  options,
  onChange,
  ariaLabel,
  className = '',
  disabled = false,
}: AuraSelectProps<T>) {
  const [open, setOpen] = useState(false);
  const [menuStyle, setMenuStyle] = useState<CSSProperties>({});
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuId = useId();
  const selected = options.find(option => option.value === value) ?? options[0];

  useEffect(() => {
    if (!open) return;

    function positionMenu() {
      const trigger = triggerRef.current;
      if (!trigger) return;
      const rect = trigger.getBoundingClientRect();
      const viewportPadding = 12;
      const width = Math.min(
        Math.max(rect.width, 320),
        window.innerWidth - viewportPadding * 2,
      );
      const estimatedHeight = Math.min(options.length * 72 + 16, 380);
      const spaceBelow = window.innerHeight - rect.bottom - viewportPadding;
      const placeAbove = spaceBelow < estimatedHeight && rect.top > spaceBelow;
      const left = Math.min(
        Math.max(viewportPadding, rect.left),
        window.innerWidth - width - viewportPadding,
      );
      const top = placeAbove
        ? Math.max(viewportPadding, rect.top - estimatedHeight - 8)
        : rect.bottom + 8;

      setMenuStyle({ left, top, width, maxHeight: Math.max(180, window.innerHeight - top - 12) });
    }

    function closeOnOutsidePointer(event: MouseEvent) {
      const target = event.target as Node;
      if (!rootRef.current?.contains(target) && !menuRef.current?.contains(target)) setOpen(false);
    }

    function closeOnEscape(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }

    positionMenu();
    document.addEventListener('mousedown', closeOnOutsidePointer);
    document.addEventListener('keydown', closeOnEscape);
    window.addEventListener('resize', positionMenu);
    window.addEventListener('scroll', positionMenu, true);
    const focusTimer = window.setTimeout(() => {
      menuRef.current?.querySelector<HTMLButtonElement>('[aria-selected="true"]')?.focus();
    });

    return () => {
      window.clearTimeout(focusTimer);
      document.removeEventListener('mousedown', closeOnOutsidePointer);
      document.removeEventListener('keydown', closeOnEscape);
      window.removeEventListener('resize', positionMenu);
      window.removeEventListener('scroll', positionMenu, true);
    };
  }, [open, options.length]);

  function moveOptionFocus(event: KeyboardEvent<HTMLButtonElement>, direction: -1 | 1) {
    if (!menuRef.current) return;
    const buttons = Array.from(
      menuRef.current.querySelectorAll<HTMLButtonElement>('.aura-select-option:not(:disabled)'),
    );
    const currentIndex = buttons.indexOf(event.currentTarget);
    buttons[(currentIndex + direction + buttons.length) % buttons.length]?.focus();
  }

  function selectOption(option: AuraSelectOption<T>) {
    if (disabled || option.disabled) return;
    onChange(option.value);
    setOpen(false);
    window.setTimeout(() => triggerRef.current?.focus());
  }

  if (!selected) return null;

  return (
    <div ref={rootRef} className={`aura-select ${open ? 'open' : ''} ${className}`}>
      <button
        ref={triggerRef}
        type="button"
        className="aura-select-trigger"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={menuId}
        disabled={disabled}
        onClick={() => setOpen(current => !current)}
        onKeyDown={event => {
          if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(event.key) && !open) {
            event.preventDefault();
            setOpen(true);
          }
        }}
      >
        {selected.icon && <span className={`aura-select-leading ${selected.tone ?? 'teal'}`}><Icon name={selected.icon} size={18} /></span>}
        <span className="aura-select-current">{selected.label}</span>
        <span className="aura-select-chevron"><Icon name="chevron-down" size={16} /></span>
      </button>

      {open && createPortal(
        <div
          ref={menuRef}
          id={menuId}
          className="aura-select-menu"
          role="listbox"
          aria-label={ariaLabel}
          style={menuStyle}
        >
          {options.map((option, index) => {
            const isSelected = option.value === value;
            const tone = option.tone ?? 'teal';
            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={isSelected}
                disabled={option.disabled}
                className={`aura-select-option ${tone}`}
                onClick={() => selectOption(option)}
                onKeyDown={event => {
                  if (event.key === 'ArrowDown') { event.preventDefault(); moveOptionFocus(event, 1); }
                  if (event.key === 'ArrowUp') { event.preventDefault(); moveOptionFocus(event, -1); }
                  if (event.key === 'Home') {
                    event.preventDefault();
                    menuRef.current?.querySelector<HTMLButtonElement>('.aura-select-option:not(:disabled)')?.focus();
                  }
                  if (event.key === 'End') {
                    event.preventDefault();
                    const available = menuRef.current?.querySelectorAll<HTMLButtonElement>('.aura-select-option:not(:disabled)');
                    available?.[available.length - 1]?.focus();
                  }
                }}
              >
                <span className="aura-select-option-icon">
                  {option.icon ? <Icon name={option.icon} size={20} /> : <span>{index + 1}</span>}
                </span>
                <span className="aura-select-option-copy">
                  <strong>{option.label}</strong>
                  {option.description && <small>{option.description}</small>}
                </span>
                <span className="aura-select-check" aria-hidden="true">{isSelected ? '✓' : ''}</span>
              </button>
            );
          })}
        </div>,
        document.body,
      )}
    </div>
  );
}

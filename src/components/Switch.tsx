import React from 'react';

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
  ariaLabel?: string;
}

export const Switch: React.FC<SwitchProps> = ({
  checked,
  onChange,
  disabled = false,
  size = 'md',
  ariaLabel,
}) => {
  const dimensions = {
    sm: { width: 34, height: 20, thumb: 14, translate: 14, pad: 3 },
    md: { width: 44, height: 24, thumb: 18, translate: 20, pad: 3 },
    lg: { width: 52, height: 28, thumb: 22, translate: 24, pad: 3 },
  }[size];

  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={(e) => {
        e.stopPropagation();
        if (!disabled) onChange(!checked);
      }}
      style={{
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        width: dimensions.width,
        height: dimensions.height,
        padding: dimensions.pad,
        borderRadius: 9999,
        background: checked
          ? 'linear-gradient(135deg, var(--accent, #ffffff) 0%, rgba(255, 255, 255, 0.85) 100%)'
          : 'rgba(255, 255, 255, 0.1)',
        border: checked
          ? '1px solid rgba(255, 255, 255, 0.4)'
          : '1px solid rgba(255, 255, 255, 0.12)',
        boxShadow: checked
          ? '0 0 14px var(--accent-glow, rgba(255, 255, 255, 0.3)), inset 0 1px 1px rgba(255, 255, 255, 0.4)'
          : 'inset 0 1px 2px rgba(0, 0, 0, 0.3)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.4 : 1,
        transition: 'all 0.24s cubic-bezier(0.16, 1, 0.3, 1)',
        outline: 'none',
        flexShrink: 0,
      }}
    >
      <span
        style={{
          display: 'block',
          width: dimensions.thumb,
          height: dimensions.thumb,
          borderRadius: '50%',
          background: checked ? '#09090b' : '#ffffff',
          boxShadow: '0 2px 6px rgba(0, 0, 0, 0.35)',
          transform: checked ? `translateX(${dimensions.translate}px)` : 'translateX(0)',
          transition: 'transform 0.24s cubic-bezier(0.16, 1, 0.3, 1), background 0.2s ease',
        }}
      />
    </button>
  );
};

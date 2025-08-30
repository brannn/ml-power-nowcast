'use client'

import { useTheme } from '@/components/ThemeProvider'

interface ToggleProps {
  leftLabel: string
  rightLabel: string
  isRight: boolean
  onToggle: () => void
  className?: string
}

export default function Toggle({
  leftLabel,
  rightLabel,
  isRight,
  onToggle,
  className = ''
}: ToggleProps) {
  const { theme } = useTheme()

  return (
    <div className={`flex items-center gap-1.5 text-xs py-1 ${className}`}>
      {/* Left Label */}
      <span className={`font-normal text-xs ${
        !isRight
          ? (theme === 'dark' ? 'text-white' : 'text-slate-900')
          : (theme === 'dark' ? 'text-slate-400' : 'text-slate-500')
      }`}>
        {leftLabel}
      </span>

      {/* Toggle Switch */}
      <button
        onClick={onToggle}
        className={`relative inline-flex h-4 w-7 items-center rounded-full transition-colors focus:outline-none focus:ring-1 focus:ring-blue-500 focus:ring-offset-1 ${
          isRight
            ? 'bg-blue-600'
            : (theme === 'dark' ? 'bg-slate-600' : 'bg-slate-400')
        }`}
      >
        {/* Sliding Circle */}
        <span
          className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
            isRight ? 'translate-x-3.5' : 'translate-x-0.5'
          }`}
        />
      </button>

      {/* Right Label */}
      <span className={`font-normal text-xs ${
        isRight
          ? (theme === 'dark' ? 'text-white' : 'text-slate-900')
          : (theme === 'dark' ? 'text-slate-400' : 'text-slate-500')
      }`}>
        {rightLabel}
      </span>
    </div>
  )
}

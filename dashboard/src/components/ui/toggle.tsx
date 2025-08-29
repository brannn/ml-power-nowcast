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
    <div className={`flex items-center gap-3 text-sm ${className}`}>
      {/* Left Label */}
      <span className={`font-medium ${
        !isRight
          ? (theme === 'dark' ? 'text-white' : 'text-slate-900')
          : (theme === 'dark' ? 'text-slate-400' : 'text-slate-500')
      }`}>
        {leftLabel}
      </span>

      {/* Toggle Switch */}
      <button
        onClick={onToggle}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
          isRight
            ? 'bg-blue-600'
            : (theme === 'dark' ? 'bg-slate-600' : 'bg-slate-300')
        }`}
      >
        {/* Sliding Circle */}
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            isRight ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>

      {/* Right Label */}
      <span className={`font-medium ${
        isRight
          ? (theme === 'dark' ? 'text-white' : 'text-slate-900')
          : (theme === 'dark' ? 'text-slate-400' : 'text-slate-500')
      }`}>
        {rightLabel}
      </span>
    </div>
  )
}

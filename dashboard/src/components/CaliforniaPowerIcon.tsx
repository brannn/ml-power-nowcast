import React from 'react'

interface CaliforniaPowerIconProps {
  size?: number
  className?: string
  animated?: boolean
}

const CaliforniaPowerIcon: React.FC<CaliforniaPowerIconProps> = ({ 
  size = 32, 
  className = "",
  animated = false 
}) => {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 32 32" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* California State Outline - More accurate shape */}
      <path
        d="M20 2 L22 3 L24 4 L26 6 L27 8 L28 10 L28 12 L27 14 L26 16 L25 18 L24 20 L23 22 L22 24 L20 26 L18 27 L16 28 L14 28 L12 27 L10 26 L8 24 L6 22 L5 20 L4 18 L3 16 L2 14 L2 12 L3 10 L4 8 L5 6 L6 4 L8 3 L10 2 L12 2 L14 2 L16 2 L18 2 L20 2 Z"
        stroke="currentColor"
        strokeWidth="2"
        fill="rgba(59, 130, 246, 0.1)"
      />
      
      {/* Power Waveform inside California */}
      <g clipPath="url(#california-clip)">
        {/* Main waveform representing power demand fluctuations */}
        <path
          d="M4 15 L6 12 L8 18 L10 10 L12 16 L14 8 L16 14 L18 11 L20 17 L22 9 L24 15 L26 13 L28 16"
          stroke="currentColor"
          strokeWidth="2.5"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={animated ? "animate-pulse" : ""}
        />

        {/* Secondary waveform for depth */}
        <path
          d="M4 17 L6 14 L8 20 L10 12 L12 18 L14 10 L16 16 L18 13 L20 19 L22 11 L24 17 L26 15 L28 18"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.5"
          className={animated ? "animate-pulse" : ""}
          style={animated ? { animationDelay: '0.5s' } : {}}
        />
      </g>
      
      {/* Clipping path to keep waveform inside California outline */}
      <defs>
        <clipPath id="california-clip">
          <path d="M20 2 L22 3 L24 4 L26 6 L27 8 L28 10 L28 12 L27 14 L26 16 L25 18 L24 20 L23 22 L22 24 L20 26 L18 27 L16 28 L14 28 L12 27 L10 26 L8 24 L6 22 L5 20 L4 18 L3 16 L2 14 L2 12 L3 10 L4 8 L5 6 L6 4 L8 3 L10 2 L12 2 L14 2 L16 2 L18 2 L20 2 Z"/>
        </clipPath>
      </defs>
    </svg>
  )
}

export default CaliforniaPowerIcon

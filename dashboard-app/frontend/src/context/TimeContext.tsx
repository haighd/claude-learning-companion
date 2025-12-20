import { createContext, useContext, ReactNode, useState, useCallback } from 'react'

interface TimeRange {
  start: Date
  end: Date
}

interface TimeContextType {
  // Current time being viewed (null = live mode)
  currentTime: Date | null

  // Time range for queries
  timeRange: TimeRange

  // Whether viewing live data or historical
  isLive: boolean

  // Playback state for auto-progression through time
  isPlaying: boolean
  playbackSpeed: number // 1x, 2x, 5x, etc.

  // Actions
  setCurrentTime: (time: Date | null) => void
  setTimeRange: (range: TimeRange) => void
  setLiveMode: (live: boolean) => void
  setPlaying: (playing: boolean) => void
  setPlaybackSpeed: (speed: number) => void

  // Convenience presets
  goToNow: () => void
  goToLastHour: () => void
  goToLastDay: () => void
  goToLastWeek: () => void
}

const TimeContext = createContext<TimeContextType | undefined>(undefined)

export function TimeProvider({ children }: { children: ReactNode }) {
  const [currentTime, setCurrentTimeState] = useState<Date | null>(null)
  const [isLive, setIsLive] = useState(true)
  const [isPlaying, setIsPlaying] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState(1)

  // Default time range: last 24 hours to now
  const [timeRange, setTimeRangeState] = useState<TimeRange>(() => {
    const end = new Date()
    const start = new Date(end.getTime() - 24 * 60 * 60 * 1000)
    return { start, end }
  })

  const setCurrentTime = useCallback((time: Date | null) => {
    setCurrentTimeState(time)
    if (time !== null) {
      setIsLive(false)
    }
  }, [])

  const setTimeRange = useCallback((range: TimeRange) => {
    setTimeRangeState(range)
    // When setting a time range, exit live mode
    setIsLive(false)
  }, [])

  const setLiveMode = useCallback((live: boolean) => {
    setIsLive(live)
    if (live) {
      setCurrentTimeState(null)
      setIsPlaying(false)
      // Update time range to end at "now"
      const end = new Date()
      const start = new Date(end.getTime() - 24 * 60 * 60 * 1000)
      setTimeRangeState({ start, end })
    }
  }, [])

  const setPlaying = useCallback((playing: boolean) => {
    setIsPlaying(playing)
    if (playing && isLive) {
      // Can't play in live mode
      setIsLive(false)
    }
  }, [isLive])

  // Convenience presets
  const goToNow = useCallback(() => {
    setLiveMode(true)
  }, [setLiveMode])

  const goToLastHour = useCallback(() => {
    const end = new Date()
    const start = new Date(end.getTime() - 60 * 60 * 1000)
    setTimeRange({ start, end })
    setCurrentTime(end)
  }, [setTimeRange, setCurrentTime])

  const goToLastDay = useCallback(() => {
    const end = new Date()
    const start = new Date(end.getTime() - 24 * 60 * 60 * 1000)
    setTimeRange({ start, end })
    setCurrentTime(end)
  }, [setTimeRange, setCurrentTime])

  const goToLastWeek = useCallback(() => {
    const end = new Date()
    const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000)
    setTimeRange({ start, end })
    setCurrentTime(end)
  }, [setTimeRange, setCurrentTime])

  const value: TimeContextType = {
    currentTime,
    timeRange,
    isLive,
    isPlaying,
    playbackSpeed,
    setCurrentTime,
    setTimeRange,
    setLiveMode,
    setPlaying,
    setPlaybackSpeed,
    goToNow,
    goToLastHour,
    goToLastDay,
    goToLastWeek,
  }

  return (
    <TimeContext.Provider value={value}>
      {children}
    </TimeContext.Provider>
  )
}

export const useTimeContext = () => {
  const context = useContext(TimeContext)
  if (!context) {
    throw new Error('useTimeContext must be used within TimeProvider')
  }
  return context
}

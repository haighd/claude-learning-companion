import { useState } from 'react'
import { useTimeContext } from '../context/TimeContext'
import { Play, Pause, SkipBack, SkipForward, Radio, Clock } from 'lucide-react'

export function TimeControls() {
  const {
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
  } = useTimeContext()

  const [showCustomRange, setShowCustomRange] = useState(false)
  const [customStart, setCustomStart] = useState('')
  const [customEnd, setCustomEnd] = useState('')

  const handlePreset = (preset: string) => {
    switch (preset) {
      case 'now':
        goToNow()
        break
      case 'hour':
        goToLastHour()
        break
      case 'day':
        goToLastDay()
        break
      case 'week':
        goToLastWeek()
        break
      case 'custom':
        setShowCustomRange(true)
        break
    }
  }

  const handleCustomRange = () => {
    if (customStart && customEnd) {
      const start = new Date(customStart)
      const end = new Date(customEnd)
      setTimeRange({ start, end })
      setCurrentTime(end)
      setShowCustomRange(false)
    }
  }

  const handlePlayPause = () => {
    if (isLive) {
      // Can't play in live mode - switch to historical first
      goToLastHour()
      setPlaying(true)
    } else {
      setPlaying(!isPlaying)
    }
  }

  const handleSkipBack = () => {
    if (currentTime) {
      const newTime = new Date(currentTime.getTime() - 60000) // 1 minute back
      if (newTime >= timeRange.start) {
        setCurrentTime(newTime)
      } else {
        setCurrentTime(timeRange.start)
      }
    }
  }

  const handleSkipForward = () => {
    if (currentTime) {
      const newTime = new Date(currentTime.getTime() + 60000) // 1 minute forward
      if (newTime <= timeRange.end) {
        setCurrentTime(newTime)
      } else {
        setCurrentTime(timeRange.end)
      }
    }
  }

  const speedOptions = [0.5, 1, 2, 5, 10]

  return (
    <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-2">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        {/* Left: Mode indicator and presets */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            {isLive ? (
              <Radio className="w-4 h-4 text-green-500 animate-pulse" />
            ) : (
              <Clock className="w-4 h-4 text-amber-500" />
            )}
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {isLive ? 'Live' : 'Historical'}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePreset('now')}
              className={`px-3 py-1 text-xs rounded ${
                isLive
                  ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400'
              }`}
            >
              Now
            </button>
            <button
              onClick={() => handlePreset('hour')}
              className="px-3 py-1 text-xs rounded bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400"
            >
              Last Hour
            </button>
            <button
              onClick={() => handlePreset('day')}
              className="px-3 py-1 text-xs rounded bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400"
            >
              Last Day
            </button>
            <button
              onClick={() => handlePreset('week')}
              className="px-3 py-1 text-xs rounded bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400"
            >
              Last Week
            </button>
            <button
              onClick={() => handlePreset('custom')}
              className="px-3 py-1 text-xs rounded bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400"
            >
              Custom
            </button>
          </div>
        </div>

        {/* Center: Playback controls (only in historical mode) */}
        {!isLive && currentTime && (
          <div className="flex items-center gap-3">
            <button
              onClick={handleSkipBack}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
              title="Skip back 1 minute"
            >
              <SkipBack className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>

            <button
              onClick={handlePlayPause}
              className="p-2 rounded-full bg-blue-500 hover:bg-blue-600 text-white"
              title={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? (
                <Pause className="w-4 h-4" />
              ) : (
                <Play className="w-4 h-4" />
              )}
            </button>

            <button
              onClick={handleSkipForward}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
              title="Skip forward 1 minute"
            >
              <SkipForward className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>

            <select
              value={playbackSpeed}
              onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
              className="px-2 py-1 text-xs rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-none"
            >
              {speedOptions.map((speed) => (
                <option key={speed} value={speed}>
                  {speed}x
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Right: Current time display */}
        <div className="text-sm text-gray-600 dark:text-gray-400">
          {isLive ? (
            <span>Viewing live data</span>
          ) : currentTime ? (
            <span>
              {currentTime.toLocaleString()} ({timeRange.start.toLocaleString()} - {timeRange.end.toLocaleString()})
            </span>
          ) : (
            <span>
              {timeRange.start.toLocaleString()} - {timeRange.end.toLocaleString()}
            </span>
          )}
        </div>
      </div>

      {/* Custom range picker modal */}
      {showCustomRange && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
              Select Custom Time Range
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Start Time
                </label>
                <input
                  type="datetime-local"
                  value={customStart}
                  onChange={(e) => setCustomStart(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  End Time
                </label>
                <input
                  type="datetime-local"
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowCustomRange(false)}
                className="px-4 py-2 text-sm rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={handleCustomRange}
                className="px-4 py-2 text-sm rounded bg-blue-500 text-white hover:bg-blue-600"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

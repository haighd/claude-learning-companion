import { useTimeContext } from '../context/TimeContext'

/**
 * Hook for managing time-based queries.
 * Returns query parameters to add to API calls.
 * Note: Playback controls are handled in TimeControls component.
 */
export function useTimeTravel() {
  const { currentTime, timeRange, isLive, isPlaying, playbackSpeed } = useTimeContext()

  /**
   * Get query parameters to add to API calls
   */
  const getQueryParams = (): Record<string, string> => {
    if (isLive) {
      return {}
    }

    const params: Record<string, string> = {}

    if (currentTime) {
      params.at_time = currentTime.toISOString()
    } else {
      // Use time range
      params.time_range = `${timeRange.start.toISOString()}/${timeRange.end.toISOString()}`
    }

    return params
  }

  /**
   * Build URL with time parameters
   */
  const buildUrl = (baseUrl: string): string => {
    const params = getQueryParams()
    if (Object.keys(params).length === 0) {
      return baseUrl
    }

    const url = new URL(baseUrl, window.location.origin)
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, value)
    })
    return url.pathname + url.search
  }

  return {
    currentTime,
    timeRange,
    isLive,
    isPlaying,
    playbackSpeed,
    getQueryParams,
    buildUrl,
  }
}

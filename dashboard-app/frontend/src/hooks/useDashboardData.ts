import { useState, useEffect, useCallback, useMemo } from 'react'
import { Stats, Hotspot, ApiRun, RawEvent, TimelineData, ApiAnomaly } from '../types'
import { useAPI } from './useAPI'
import { useTimeTravel } from './useTimeTravel'

export function useDashboardData() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [hotspots, setHotspots] = useState<Hotspot[]>([])
  const [runs, setRuns] = useState<ApiRun[]>([])
  const [events, setEvents] = useState<RawEvent[]>([])
  const [timeline, setTimeline] = useState<TimelineData | null>(null)
  const [anomalies, setAnomalies] = useState<ApiAnomaly[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const api = useAPI()
  const { buildUrl, isLive, currentTime } = useTimeTravel()

  const loadData = useCallback(async () => {
    try {
      const [statsData, hotspotsData, runsData, timelineData, anomaliesData, eventsData] = await Promise.all([
        api.get(buildUrl('/api/stats')).catch(() => null),
        api.get(buildUrl('/api/hotspots')).catch(() => []),
        api.get(buildUrl('/api/runs?limit=100')).catch(() => []),
        api.get(buildUrl('/api/timeline')).catch(() => null),
        api.get(buildUrl('/api/anomalies')).catch(() => []),
        api.get(buildUrl('/api/events?limit=100')).catch(() => []),
      ])
      if (statsData) setStats(statsData)
      setHotspots(hotspotsData || [])
      setRuns(runsData || [])
      if (timelineData) setTimeline(timelineData)
      setAnomalies(anomaliesData || [])
      setEvents(eventsData || [])
    } catch (err) {
      console.error('Failed to load dashboard data:', err)
    } finally {
      setIsLoading(false)
    }
  }, [api, buildUrl])

  const reload = useCallback(() => {
    setIsLoading(true)
    loadData()
  }, [loadData])

  const loadStats = useCallback(async () => {
    try {
      const data = await api.get(buildUrl('/api/stats'))
      if (data) setStats(data)
    } catch (err) {
      console.error('Failed to load stats:', err)
    }
  }, [api, buildUrl])

  // Initial data load and refresh when time changes
  useEffect(() => {
    loadData()
  }, [loadData, currentTime, isLive]) // Reload when time context changes

  // Auto-refresh only in live mode
  useEffect(() => {
    if (!isLive) {
      // Don't auto-refresh in historical mode
      return
    }

    // Auto-refresh stats, runs, and events every 10 seconds
    const interval = setInterval(() => {
      // Refresh stats
      api.get(buildUrl('/api/stats')).then(data => {
        if (data) setStats(data)
      }).catch(() => {})
      // Refresh runs
      api.get(buildUrl('/api/runs?limit=100')).then(data => {
        if (data) setRuns(data)
      }).catch(() => {})
      // Refresh events
      api.get(buildUrl('/api/events?limit=100')).then(data => {
        if (data) setEvents(data)
      }).catch(() => {})
    }, 10000)

    return () => clearInterval(interval)
  }, [api, buildUrl, isLive])

  return useMemo(() => ({
    stats,
    hotspots,
    runs,
    events,
    timeline,
    anomalies,
    isLoading,
    reload,
    loadStats,
    setStats,
    setAnomalies,
  }), [stats, hotspots, runs, events, timeline, anomalies, isLoading, reload, loadStats])
}

import { useState, useMemo, useEffect, useRef, useCallback } from 'react'
import { TimelineEvent, Heuristic } from '../types'
import { Clock, Play, Pause, SkipBack, SkipForward, CheckCircle, CheckSquare, XCircle, Brain, Star, AlertTriangle, FileText, Terminal, Cpu, Globe, Workflow } from 'lucide-react'
import { format } from 'date-fns'
import { parseUTCTimestamp, formatLocalTime } from '../utils/formatDate'

interface TimelineViewProps {
  events: TimelineEvent[]
  heuristics: Heuristic[]
  onEventClick: (event: TimelineEvent) => void
}

const eventConfig = {
  // Heuristic events
  heuristic_validated: { icon: CheckCircle, color: 'bg-emerald-500', label: 'Heuristic Validated' },
  heuristic_violated: { icon: XCircle, color: 'bg-red-500', label: 'Heuristic Violated' },
  // Learning events
  auto_failure_capture: { icon: AlertTriangle, color: 'bg-orange-500', label: 'Failure Captured' },
  golden_rule_promotion: { icon: Star, color: 'bg-amber-500', label: 'Golden Rule Promoted' },
  task_outcome: { icon: CheckSquare, color: 'bg-sky-500', label: 'Task Outcome' },
  // Tool types
  bash_run: { icon: Terminal, color: 'bg-green-500', label: 'Bash Command' },
  task_run: { icon: Workflow, color: 'bg-blue-500', label: 'Task Agent' },
  mcp_call: { icon: Cpu, color: 'bg-purple-500', label: 'MCP Call' },
  webfetch_call: { icon: Globe, color: 'bg-teal-500', label: 'Web Fetch' },
  workflow_run: { icon: Play, color: 'bg-slate-500', label: 'Workflow Run' },
}

/**
 * Feature flag for playback controls.
 * Hidden until session replay features are implemented.
 * See: https://github.com/haighd/claude-learning-companion/issues/25 (Session Replay)
 *      https://github.com/haighd/claude-learning-companion/issues/26 (Time-Scrubbing)
 *      https://github.com/haighd/claude-learning-companion/issues/27 (Debug Stepping)
 */
const ENABLE_PLAYBACK_CONTROLS = false

export default function TimelineView({ events, heuristics, onEventClick }: TimelineViewProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [playbackIndex, setPlaybackIndex] = useState(0)
  const [filterType, setFilterType] = useState<string | null>(null)
  const [speed, setSpeed] = useState(1)

  // Refs for playback (avoid useEffect dependency issues per golden rule #9)
  const eventRefs = useRef<Map<number, HTMLDivElement>>(new Map())
  const playbackRef = useRef({ isPlaying, speed, playbackIndex })

  // Keep ref in sync with state
  useEffect(() => {
    playbackRef.current = { isPlaying, speed, playbackIndex }
  }, [isPlaying, speed, playbackIndex])

  // Group events by date
  const groupedEvents = useMemo(() => {
    const filtered = filterType
      ? events.filter(e => e.event_type === filterType)
      : events

    const groups: { [key: string]: TimelineEvent[] } = {}
    filtered.forEach(event => {
      const parsedDate = parseUTCTimestamp(event.timestamp)
      const date = parsedDate ? format(parsedDate, 'yyyy-MM-dd') : 'unknown'
      if (!groups[date]) groups[date] = []
      groups[date].push(event)
    })
    return groups
  }, [events, filterType])

  const dates = Object.keys(groupedEvents).sort().reverse()

  // Flat list of events in display order (for playback navigation)
  const orderedEvents = useMemo(() => {
    const result: TimelineEvent[] = []
    dates.forEach(date => {
      result.push(...groupedEvents[date])
    })
    return result
  }, [dates, groupedEvents])

  // Reset playback index when filter changes or events update
  useEffect(() => {
    setPlaybackIndex(0)
    setIsPlaying(false)
  }, [filterType, events.length])

  // Auto-play effect
  useEffect(() => {
    if (!isPlaying || orderedEvents.length === 0) return

    const intervalMs = 1500 / speed // Base interval of 1.5s, adjusted by speed

    const interval = setInterval(() => {
      setPlaybackIndex(prev => {
        const next = prev + 1
        if (next >= orderedEvents.length) {
          setIsPlaying(false)
          return prev
        }
        return next
      })
    }, intervalMs)

    return () => clearInterval(interval)
  }, [isPlaying, speed, orderedEvents.length])

  // Scroll current event into view
  useEffect(() => {
    if (orderedEvents.length === 0) return
    const currentEvent = orderedEvents[playbackIndex]
    if (!currentEvent) return

    const element = eventRefs.current.get(currentEvent.id)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [playbackIndex, orderedEvents])

  // Playback controls
  const handlePlayPause = useCallback(() => {
    if (orderedEvents.length === 0) return
    // If at end, restart from beginning
    if (playbackIndex >= orderedEvents.length - 1 && !isPlaying) {
      setPlaybackIndex(0)
    }
    setIsPlaying(prev => !prev)
  }, [orderedEvents.length, playbackIndex, isPlaying])

  const handleSkipBack = useCallback(() => {
    setPlaybackIndex(prev => Math.max(0, prev - 1))
  }, [])

  const handleSkipForward = useCallback(() => {
    setPlaybackIndex(prev => Math.min(orderedEvents.length - 1, prev + 1))
  }, [orderedEvents.length])

  const getEventIcon = (type: string) => {
    const config = eventConfig[type as keyof typeof eventConfig]
    return config?.icon || FileText
  }

  const getEventColor = (type: string) => {
    const config = eventConfig[type as keyof typeof eventConfig]
    return config?.color || 'bg-slate-500'
  }

  const getHeuristicById = (id: number) => heuristics.find(h => h.id === id)

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Clock className="w-5 h-5 text-cyan-400" />
          <h3 className="text-lg font-semibold text-white">Timeline</h3>
          <span className="text-sm text-slate-400">({events.length} events)</span>
        </div>

        {/* Playback controls - hidden via ENABLE_PLAYBACK_CONTROLS feature flag */}
        {ENABLE_PLAYBACK_CONTROLS && (
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 bg-slate-700 rounded-lg p-1">
              <button
                onClick={handleSkipBack}
                className="p-1.5 rounded hover:bg-slate-600 text-slate-400 hover:text-white transition"
              >
                <SkipBack className="w-4 h-4" />
              </button>
              <button
                onClick={handlePlayPause}
                className={`p-1.5 rounded transition ${isPlaying ? 'bg-sky-500 text-white' : 'hover:bg-slate-600 text-slate-400 hover:text-white'}`}
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </button>
              <button
                onClick={handleSkipForward}
                className="p-1.5 rounded hover:bg-slate-600 text-slate-400 hover:text-white transition"
              >
                <SkipForward className="w-4 h-4" />
              </button>
            </div>

            <select
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              className="bg-slate-700 text-sm text-white rounded-md px-2 py-1 border border-slate-600"
              aria-label="Playback speed"
            >
              <option value={0.5}>0.5x</option>
              <option value={1}>1x</option>
              <option value={2}>2x</option>
              <option value={5}>5x</option>
            </select>

            {orderedEvents.length > 0 && (
              <div className="flex items-center space-x-2 text-sm text-slate-400">
                <span>{playbackIndex + 1}</span>
                <span>/</span>
                <span>{orderedEvents.length}</span>
              </div>
            )}
          </div>
        )}

        <div className="flex items-center space-x-4">
          {/* Filter */}
          <select
            value={filterType || ''}
            onChange={(e) => setFilterType(e.target.value || null)}
            className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600"
            aria-label="Filter events by type"
          >
            <option value="">All Events</option>
            {Object.entries(eventConfig).map(([type, config]) => (
              <option key={type} value={type}>{config.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Event type legend */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        {Object.entries(eventConfig).map(([type, config]) => (
          <button
            key={type}
            onClick={() => setFilterType(filterType === type ? null : type)}
            className={`flex items-center space-x-1.5 px-2 py-1 rounded-full text-xs transition
              ${filterType === type ? 'bg-white/10 ring-1 ring-white/20' : 'hover:bg-white/5'}`}
          >
            <div className={`w-2 h-2 rounded-full ${config.color}`} />
            <span className="text-slate-300">{config.label}</span>
          </button>
        ))}
      </div>

      {/* Timeline */}
      <div className="space-y-6 max-h-[600px] overflow-y-auto pr-2">
        {dates.map(date => (
          <div key={date}>
            <div className="sticky top-0 bg-slate-800 py-2 z-10">
              <h4 className="text-sm font-medium text-slate-400">{date !== 'unknown' ? format(new Date(date), 'EEEE, MMMM d, yyyy') : 'Unknown Date'}</h4>
            </div>

            <div className="relative ml-4 border-l-2 border-slate-700">
              {groupedEvents[date].map((event) => {
                const Icon = getEventIcon(event.event_type)
                const color = getEventColor(event.event_type)
                const config = eventConfig[event.event_type as keyof typeof eventConfig]
                const isCurrentPlayback = orderedEvents[playbackIndex]?.id === event.id

                return (
                  <div
                    key={event.id}
                    ref={(el) => {
                      if (el) eventRefs.current.set(event.id, el)
                      else eventRefs.current.delete(event.id)
                    }}
                    className={`relative pl-6 pb-4 cursor-pointer group transition-all duration-300 ${
                      isCurrentPlayback ? 'scale-[1.02]' : ''
                    }`}
                    onClick={() => {
                      // Set playback position when clicking an event
                      const idx = orderedEvents.findIndex(e => e.id === event.id)
                      if (idx !== -1) setPlaybackIndex(idx)
                      onEventClick(event)
                    }}
                  >
                    {/* Timeline dot */}
                    <div className={`absolute left-0 top-0 -translate-x-1/2 w-4 h-4 rounded-full ${color} flex items-center justify-center ring-4 ${
                      isCurrentPlayback ? 'ring-cyan-500 ring-2' : 'ring-slate-800'
                    } transition-all duration-300`}>
                      <Icon className="w-2.5 h-2.5 text-white" />
                    </div>

                    {/* Event card */}
                    <div className={`rounded-lg p-3 transition-all duration-300 ${
                      isCurrentPlayback
                        ? 'bg-slate-600 ring-2 ring-cyan-500/50 shadow-lg shadow-cyan-500/20'
                        : 'bg-slate-700/50 group-hover:bg-slate-700'
                    }`}>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="text-sm font-medium text-white">{config?.label || event.event_type}</span>
                            {event.domain && (
                              <span className="px-1.5 py-0.5 rounded bg-slate-600 text-xs text-slate-300">{event.domain}</span>
                            )}
                          </div>
                          <p className="text-sm text-slate-300">{event.description}</p>

                          {/* Show related heuristic if applicable */}
                          {event.metadata?.heuristic_id && (
                            <div className="mt-2 p-2 bg-slate-800/50 rounded text-xs">
                              <div className="flex items-center space-x-1 text-violet-400 mb-1">
                                <Brain className="w-3 h-3" />
                                <span>Related Heuristic</span>
                              </div>
                              <div className="text-slate-300">
                                {getHeuristicById(event.metadata.heuristic_id)?.rule || `Heuristic #${event.metadata.heuristic_id}`}
                              </div>
                            </div>
                          )}

                          {/* Show file path if available */}
                          {event.file_path && (
                            <div className="mt-2 flex items-center space-x-1 text-xs text-sky-400">
                              <FileText className="w-3 h-3" />
                              <span>{event.file_path}</span>
                              {event.line_number && <span>:{event.line_number}</span>}
                            </div>
                          )}
                        </div>

                        <div className="text-xs text-slate-500 ml-4 flex-shrink-0">
                          {formatLocalTime(event.timestamp, 'HH:mm:ss')}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}

        {dates.length === 0 && (
          <div className="text-center text-slate-400 py-12">
            No events found
          </div>
        )}
      </div>
    </div>
  )
}

import { useEffect, useRef, useCallback } from 'react'
import { X, ArrowLeft, ChevronRight, Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import { DrillDownView } from './types'
import RunsDrillDown from './RunsDrillDown'
import HeuristicsDrillDown from './HeuristicsDrillDown'
import GoldenRulesDrillDown from './GoldenRulesDrillDown'
import HotspotsDrillDown from './HotspotsDrillDown'
import QueriesDrillDown from './QueriesDrillDown'

interface StatCardData {
  label: string
  value: string | number
  icon: any
  color: string
  bgColor: string
  description: string
  drillDownType?: 'runs' | 'heuristics' | 'hotspots' | 'golden' | 'learnings' | 'queries'
  details?: { label: string; value: string | number }[]
}

interface DrillDownModalProps {
  card: StatCardData
  drillDownView: DrillDownView
  drillDownData: any
  loading: boolean
  error: string | null
  onClose: () => void
  onBack: () => void
  onLoadDrillDown: (type: DrillDownView) => void
}

export default function DrillDownModal({
  card,
  drillDownView,
  drillDownData,
  loading,
  error,
  onClose,
  onBack,
  onLoadDrillDown,
}: DrillDownModalProps) {
  const Icon = card.icon
  const modalRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  // Store the element that had focus before modal opened
  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement
    // Focus the close button when modal opens
    closeButtonRef.current?.focus()

    return () => {
      // Return focus to the element that had focus before modal opened
      previousFocusRef.current?.focus()
    }
  }, [])

  // Handle Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  // Focus trap - keep focus within modal
  const handleTabKey = useCallback((e: React.KeyboardEvent) => {
    if (e.key !== 'Tab' || !modalRef.current) return

    const focusableElements = modalRef.current.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    if (e.shiftKey && document.activeElement === firstElement) {
      e.preventDefault()
      lastElement?.focus()
    } else if (!e.shiftKey && document.activeElement === lastElement) {
      e.preventDefault()
      firstElement?.focus()
    }
  }, [])

  const renderDrillDownContent = () => {
    if (loading) {
      return (
        <div className="flex flex-col items-center justify-center py-8 gap-2" role="status" aria-live="polite">
          <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--theme-accent)' }} aria-hidden="true" />
          <span className="text-sm text-slate-400">Loading data...</span>
        </div>
      )
    }

    if (error) {
      return (
        <div className="flex flex-col items-center justify-center py-8 gap-3" role="alert">
          <AlertCircle className="w-8 h-8 text-red-400" aria-hidden="true" />
          <span className="text-sm text-red-400 text-center">{error}</span>
          <button
            onClick={() => onLoadDrillDown(drillDownView)}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500"
          >
            <RefreshCw className="w-4 h-4" aria-hidden="true" />
            Retry
          </button>
        </div>
      )
    }

    if (!drillDownData) return null

    switch (drillDownView) {
      case 'runs':
        return <RunsDrillDown data={drillDownData} cardLabel={card.label} />
      case 'heuristics':
        return <HeuristicsDrillDown data={drillDownData} />
      case 'golden':
        return <GoldenRulesDrillDown data={drillDownData} />
      case 'hotspots':
        return <HotspotsDrillDown data={drillDownData} />
      case 'queries':
        return <QueriesDrillDown data={drillDownData} />
      default:
        return null
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        aria-describedby="modal-description"
        className="glass-panel rounded-xl p-6 max-w-lg w-full shadow-2xl max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleTabKey}
      >
        <div className="flex items-center justify-between mb-4">
          {drillDownView !== 'main' ? (
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500 rounded-lg px-2 py-1"
              aria-label="Go back to main view"
            >
              <ArrowLeft className="w-4 h-4" aria-hidden="true" />
              <span className="text-sm">Back</span>
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <div className={`p-3 rounded-lg ${card.bgColor}`} aria-hidden="true">
                <Icon className={`w-6 h-6 ${card.color}`} />
              </div>
              <div>
                <h2 id="modal-title" className="text-lg font-semibold text-white">{card.label}</h2>
                <div className={`text-3xl font-bold ${card.color}`} aria-label={`Value: ${card.value}`}>
                  {card.value}
                </div>
              </div>
            </div>
          )}
          <button
            ref={closeButtonRef}
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500 rounded-lg"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {drillDownView === 'main' ? (
            <>
              <p id="modal-description" className="text-slate-300 text-sm mb-4">{card.description}</p>

              {card.details && card.details.length > 0 && (
                <div className="border-t border-slate-700 pt-4 mb-4">
                  <h3 className="text-xs font-medium text-slate-400 mb-3">DETAILS</h3>
                  <dl className="space-y-2">
                    {card.details.map((detail, idx) => (
                      <div key={idx} className="flex items-center justify-between">
                        <dt className="text-sm text-slate-400">{detail.label}</dt>
                        <dd className="text-sm font-medium text-white">{detail.value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )}

              {card.drillDownType && (
                <button
                  onClick={() => onLoadDrillDown(card.drillDownType as DrillDownView)}
                  className="w-full flex items-center justify-between p-3 bg-slate-700/50 hover:bg-slate-700 rounded-lg transition-colors group focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  aria-label={`View all ${card.label.toLowerCase()}`}
                >
                  <span className="text-sm text-slate-300 group-hover:text-white">
                    View all {card.label.toLowerCase()}
                  </span>
                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-white" aria-hidden="true" />
                </button>
              )}
            </>
          ) : (
            renderDrillDownContent()
          )}
        </div>
      </div>
    </div>
  )
}

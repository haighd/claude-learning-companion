import { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import * as d3 from 'd3'
import { Target } from 'lucide-react'
import { useTreemapData } from './useTreemapData'
import { useD3Treemap } from './useD3Treemap'
import TreemapTooltip from './TreemapTooltip'
import TreemapFilters from './TreemapFilters'
import TreemapLegend from './TreemapLegend'
import TreemapControls from './TreemapControls'
import TreemapBreadcrumbs, { type BreadcrumbItem } from './TreemapBreadcrumbs'
import HotspotDetailPanel from './HotspotDetailPanel'
import type { HotspotTreemapProps, TooltipState, ApiHotspot } from './types'

export default function HotspotTreemap({ hotspots, onSelect, selectedDomain, onDomainFilter }: HotspotTreemapProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [tooltipState, setTooltipState] = useState<TooltipState>({ x: 0, y: 0, data: null })
  const [expandedHotspot, setExpandedHotspot] = useState<string | null>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 })

  // New state for enhanced features
  const [searchQuery, setSearchQuery] = useState('')
  const [zoomTransform, setZoomTransform] = useState<d3.ZoomTransform | null>(null)
  const [focusedPath, setFocusedPath] = useState<string | null>(null)
  const [drillPath, setDrillPath] = useState<string[]>([])

  // Get data from hook
  const { domains, filteredHotspots, hierarchy } = useTreemapData(hotspots, selectedDomain)

  // Filter hotspots further by drill path (show only items under current path)
  const drilledHotspots = useMemo(() => {
    if (drillPath.length === 0) return filteredHotspots
    const pathPrefix = drillPath.join('/')
    return filteredHotspots.filter(h => h.location.startsWith(pathPrefix))
  }, [filteredHotspots, drillPath])

  // Build hierarchy from drilled hotspots
  const drilledHierarchy = useMemo(() => {
    if (drillPath.length === 0) return hierarchy

    // Find the node at the current drill path
    let currentNode = hierarchy
    for (const part of drillPath) {
      const child = currentNode.children?.find(c => c.name === part)
      if (child && child.children) {
        currentNode = child
      } else {
        break
      }
    }
    return currentNode
  }, [hierarchy, drillPath])

  // Count search matches
  const searchMatchCount = useMemo(() => {
    if (!searchQuery) return 0
    const query = searchQuery.toLowerCase()
    return drilledHotspots.filter(h =>
      h.location.toLowerCase().includes(query)
    ).length
  }, [drilledHotspots, searchQuery])

  // Breadcrumb items from drill path
  const breadcrumbItems: BreadcrumbItem[] = useMemo(() => {
    return drillPath.map((name, index) => ({
      name,
      path: drillPath.slice(0, index + 1).join('/')
    }))
  }, [drillPath])

  // Handle cell click - toggle expanded hotspot and call onSelect
  const handleCellClick = useCallback((hotspot: ApiHotspot) => {
    setExpandedHotspot(prev => prev === hotspot.location ? null : hotspot.location)
    setFocusedPath(hotspot.location)
    onSelect(hotspot.location)
  }, [onSelect])

  // Handle double-click to drill into a directory
  const handleDrillIn = useCallback((path: string) => {
    const parts = path.split(/[\/\\]/).filter(Boolean)
    // Only drill in if there's at least one more level
    if (parts.length > drillPath.length) {
      setDrillPath(parts.slice(0, drillPath.length + 1))
      setFocusedPath(null)
    }
  }, [drillPath])

  // Navigate via breadcrumbs
  const handleBreadcrumbNavigate = useCallback((path: string | null) => {
    if (path === null) {
      setDrillPath([])
    } else {
      const parts = path.split('/').filter(Boolean)
      setDrillPath(parts)
    }
    setFocusedPath(null)
  }, [])

  // Handle zoom changes
  const handleZoomChange = useCallback((transform: d3.ZoomTransform) => {
    setZoomTransform(transform)
  }, [])

  // Render D3 treemap
  const { zoomIn, zoomOut, resetZoom } = useD3Treemap({
    svgRef,
    hierarchy: drilledHierarchy,
    filteredHotspots: drilledHotspots,
    dimensions,
    onCellClick: handleCellClick,
    onTooltipChange: setTooltipState,
    searchQuery,
    zoomTransform,
    onZoomChange: handleZoomChange,
    focusedPath,
  })

  // Current zoom level (for display)
  const zoomLevel = zoomTransform?.k ?? 1

  // Handle window resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const { width } = containerRef.current.getBoundingClientRect()
        setDimensions({ width: Math.max(width - 32, 200), height: 500 })
      }
    }

    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  // Get expanded hotspot data
  const expandedHotspotData = useMemo(() => {
    if (!expandedHotspot) return null
    return drilledHotspots.find(h => h.location === expandedHotspot) || null
  }, [drilledHotspots, expandedHotspot])

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Escape to clear focus or go up one level
      if (e.key === 'Escape') {
        if (focusedPath) {
          setFocusedPath(null)
          setExpandedHotspot(null)
        } else if (drillPath.length > 0) {
          setDrillPath(prev => prev.slice(0, -1))
        }
      }
      // + or = to zoom in
      if (e.key === '+' || e.key === '=') {
        zoomIn()
      }
      // - to zoom out
      if (e.key === '-') {
        zoomOut()
      }
      // 0 to reset zoom
      if (e.key === '0') {
        resetZoom()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [focusedPath, drillPath, zoomIn, zoomOut, resetZoom])

  return (
    <div ref={containerRef} className="glass-panel rounded-lg p-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div className="flex items-center space-x-2">
          <Target className="w-5 h-5 text-orange-400" aria-hidden="true" />
          <h3 className="text-lg font-semibold text-white">Hot Spots</h3>
          <span className="text-sm text-slate-400">
            ({drilledHotspots?.length || 0} locations)
          </span>
        </div>

        <div className="flex items-center gap-4">
          <TreemapControls
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onZoomIn={zoomIn}
            onZoomOut={zoomOut}
            onResetZoom={resetZoom}
            zoomLevel={zoomLevel}
            matchCount={searchQuery ? searchMatchCount : undefined}
          />

          <TreemapFilters
            selectedDomain={selectedDomain}
            domains={domains}
            onDomainFilter={onDomainFilter}
          />
        </div>
      </div>

      {/* Breadcrumbs */}
      <TreemapBreadcrumbs
        items={breadcrumbItems}
        onNavigate={handleBreadcrumbNavigate}
      />

      {/* Legend */}
      <TreemapLegend />

      {/* Treemap */}
      <div className="relative">
        {drilledHotspots && drilledHotspots.length > 0 ? (
          <svg
            ref={svgRef}
            width={dimensions.width}
            height={dimensions.height}
            className="rounded-lg overflow-hidden bg-slate-900/50"
            aria-label="Hotspot treemap visualization"
            role="img"
          />
        ) : (
          <div
            className="h-[500px] flex flex-col items-center justify-center text-slate-400 gap-2"
            role="status"
          >
            <Target className="w-12 h-12 opacity-30" />
            <p>No hotspots found</p>
            {drillPath.length > 0 && (
              <button
                onClick={() => setDrillPath([])}
                className="text-sm text-cyan-400 hover:text-cyan-300 underline"
              >
                Go back to root
              </button>
            )}
          </div>
        )}

        <TreemapTooltip tooltipState={tooltipState} dimensions={dimensions} />

        <HotspotDetailPanel
          hotspot={expandedHotspotData}
          onClose={() => {
            setExpandedHotspot(null)
            setFocusedPath(null)
          }}
        />
      </div>

      {/* Keyboard shortcuts hint */}
      <div className="mt-3 text-xs text-slate-500 flex flex-wrap gap-x-4 gap-y-1">
        <span>
          <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-300">+</kbd>
          <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-300 ml-1">-</kbd>
          {' '}Zoom
        </span>
        <span>
          <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-300">0</kbd>
          {' '}Reset
        </span>
        <span>
          <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-300">Esc</kbd>
          {' '}Go back
        </span>
        <span>Scroll to pan</span>
      </div>
    </div>
  )
}

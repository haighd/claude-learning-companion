import { useEffect, useRef, useCallback } from 'react'
import * as d3 from 'd3'
import type { ApiHotspot, TreemapData, TooltipState } from './types'

interface UseD3TreemapProps {
  svgRef: React.RefObject<SVGSVGElement>
  hierarchy: TreemapData
  filteredHotspots: ApiHotspot[]
  dimensions: { width: number; height: number }
  onCellClick: (hotspot: ApiHotspot) => void
  onTooltipChange: (state: TooltipState) => void
  searchQuery?: string
  zoomTransform?: d3.ZoomTransform | null
  onZoomChange?: (transform: d3.ZoomTransform) => void
  focusedPath?: string | null
}

const colorScale = (severity: string | undefined) => {
  switch (severity) {
    case 'critical': return '#ef4444'
    case 'high': return '#f97316'
    case 'medium': return '#eab308'
    case 'low': return '#22c55e'
    default: return '#64748b'
  }
}

export function useD3Treemap({
  svgRef,
  hierarchy,
  filteredHotspots,
  dimensions,
  onCellClick,
  onTooltipChange,
  searchQuery = '',
  zoomTransform,
  onZoomChange,
  focusedPath,
}: UseD3TreemapProps) {
  const isDrawingRef = useRef(false)
  const tooltipRef = useRef<TooltipState>({ x: 0, y: 0, data: null })
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)
  const gRef = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null)

  // Use refs for callbacks to avoid stale closures and prevent effect re-runs
  const onCellClickRef = useRef(onCellClick)
  const onTooltipChangeRef = useRef(onTooltipChange)
  const onZoomChangeRef = useRef(onZoomChange)
  onCellClickRef.current = onCellClick
  onTooltipChangeRef.current = onTooltipChange
  onZoomChangeRef.current = onZoomChange

  // Check if a path matches the search query
  const matchesSearch = useCallback((path: string | undefined, name: string) => {
    if (!searchQuery) return false
    const query = searchQuery.toLowerCase()
    return (path?.toLowerCase().includes(query) || name.toLowerCase().includes(query))
  }, [searchQuery])

  // Main rendering effect
  useEffect(() => {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    if (!filteredHotspots || filteredHotspots.length === 0) return

    const { width, height } = dimensions

    // Check if we have any data
    if (!hierarchy.children || hierarchy.children.length === 0) return

    // Create main group for zoom/pan
    const g = svg.append('g').attr('class', 'treemap-container')
    gRef.current = g

    // Set up zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
        if (onZoomChangeRef.current) {
          onZoomChangeRef.current(event.transform)
        }
      })

    zoomRef.current = zoom
    svg.call(zoom)

    // Apply initial/stored transform
    if (zoomTransform) {
      svg.call(zoom.transform, zoomTransform)
    }

    // Build treemap
    const root = d3.hierarchy(hierarchy)
      .sum(d => d.value || 0)
      .sort((a, b) => (b.value || 0) - (a.value || 0))

    const treemap = d3.treemap<TreemapData>()
      .size([width, height])
      .padding(2)
      .round(true)

    treemap(root)

    const leaves = root.leaves() as any[]

    // Create cells
    const cells = g.selectAll('g.cell')
      .data(leaves)
      .enter()
      .append('g')
      .attr('class', 'cell')
      .attr('transform', d => `translate(${d.x0},${d.y0})`)
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation()
        const hotspot = filteredHotspots.find(h => h.location === d.data.path)
        if (hotspot) {
          onCellClickRef.current(hotspot)
        }
      })
      .on('mouseenter', (event, d) => {
        if (isDrawingRef.current) return
        const hotspot = filteredHotspots.find(h => h.location === d.data.path)
        if (hotspot) {
          const rect = svgRef.current!.getBoundingClientRect()
          tooltipRef.current = {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
            data: hotspot
          }
          onTooltipChangeRef.current(tooltipRef.current)
        }
      })
      .on('mousemove', (event) => {
        if (isDrawingRef.current || !tooltipRef.current.data) return
        const rect = svgRef.current!.getBoundingClientRect()
        tooltipRef.current.x = event.clientX - rect.left
        tooltipRef.current.y = event.clientY - rect.top
        onTooltipChangeRef.current({ ...tooltipRef.current })
      })
      .on('mouseleave', () => {
        tooltipRef.current = { x: 0, y: 0, data: null }
        onTooltipChangeRef.current({ x: 0, y: 0, data: null })
      })

    // Background rect (visual)
    cells.append('rect')
      .attr('class', 'cell-bg')
      .attr('width', d => Math.max(0, d.x1 - d.x0))
      .attr('height', d => Math.max(0, d.y1 - d.y0))
      .attr('fill', d => colorScale(d.data.severity))
      .attr('opacity', d => 0.3 + Math.min((d.data.strength || 0) * 0.1, 0.5))
      .attr('rx', 4)
      .attr('class', 'treemap-cell')

    // Border
    cells.append('rect')
      .attr('class', 'cell-border')
      .attr('width', d => Math.max(0, d.x1 - d.x0))
      .attr('height', d => Math.max(0, d.y1 - d.y0))
      .attr('fill', 'none')
      .attr('stroke', d => colorScale(d.data.severity))
      .attr('stroke-width', 1.5)
      .attr('rx', 4)

    // Search highlight ring
    cells.filter(d => matchesSearch(d.data.path, d.data.name))
      .append('rect')
      .attr('class', 'search-highlight')
      .attr('width', d => Math.max(0, d.x1 - d.x0))
      .attr('height', d => Math.max(0, d.y1 - d.y0))
      .attr('fill', 'none')
      .attr('stroke', '#00f3ff')
      .attr('stroke-width', 3)
      .attr('rx', 4)
      .attr('opacity', 0.8)
      .style('filter', 'drop-shadow(0 0 6px rgba(0, 243, 255, 0.8))')

    // Focused path highlight
    if (focusedPath) {
      cells.filter(d => d.data.path === focusedPath)
        .append('rect')
        .attr('class', 'focus-highlight')
        .attr('width', d => Math.max(0, d.x1 - d.x0))
        .attr('height', d => Math.max(0, d.y1 - d.y0))
        .attr('fill', 'rgba(0, 243, 255, 0.15)')
        .attr('stroke', '#00f3ff')
        .attr('stroke-width', 2)
        .attr('rx', 4)
    }

    // Text labels (only for cells large enough)
    cells.filter(d => (d.x1 - d.x0) > 60 && (d.y1 - d.y0) > 30)
      .append('text')
      .attr('class', 'cell-label')
      .attr('x', 6)
      .attr('y', 16)
      .attr('fill', d => matchesSearch(d.data.path, d.data.name) ? '#00f3ff' : 'white')
      .attr('font-size', '11px')
      .attr('font-weight', d => matchesSearch(d.data.path, d.data.name) ? '700' : '500')
      .style('pointer-events', 'none')
      .text(d => {
        const name = d.data.name
        const maxLen = Math.floor((d.x1 - d.x0 - 12) / 6)
        return name.length > maxLen ? name.slice(0, maxLen - 2) + '..' : name
      })

    // Hit count badge
    cells.filter(d => (d.x1 - d.x0) > 40 && (d.y1 - d.y0) > 50)
      .append('text')
      .attr('class', 'cell-hits')
      .attr('x', 6)
      .attr('y', 32)
      .attr('fill', 'rgba(255,255,255,0.7)')
      .attr('font-size', '10px')
      .style('pointer-events', 'none')
      .text(d => `${d.value} hits`)

  }, [svgRef, filteredHotspots, dimensions, hierarchy, searchQuery, focusedPath, matchesSearch, zoomTransform])

  // Zoom control functions
  const zoomIn = useCallback(() => {
    if (!svgRef.current || !zoomRef.current) return
    const svg = d3.select(svgRef.current)
    svg.transition().duration(300).call(zoomRef.current.scaleBy, 1.3)
  }, [svgRef])

  const zoomOut = useCallback(() => {
    if (!svgRef.current || !zoomRef.current) return
    const svg = d3.select(svgRef.current)
    svg.transition().duration(300).call(zoomRef.current.scaleBy, 0.7)
  }, [svgRef])

  const resetZoom = useCallback(() => {
    if (!svgRef.current || !zoomRef.current) return
    const svg = d3.select(svgRef.current)
    svg.transition().duration(300).call(zoomRef.current.transform, d3.zoomIdentity)
  }, [svgRef])

  return { zoomIn, zoomOut, resetZoom }
}

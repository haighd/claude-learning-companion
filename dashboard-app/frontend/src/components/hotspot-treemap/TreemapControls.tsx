import { ZoomIn, ZoomOut, Maximize2, Search, X } from 'lucide-react'

interface TreemapControlsProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  onZoomIn: () => void
  onZoomOut: () => void
  onResetZoom: () => void
  zoomLevel: number
  matchCount?: number
}

export default function TreemapControls({
  searchQuery,
  onSearchChange,
  onZoomIn,
  onZoomOut,
  onResetZoom,
  zoomLevel,
  matchCount,
}: TreemapControlsProps) {
  return (
    <div className="flex items-center gap-4">
      {/* Search */}
      <div className="relative flex-1 max-w-xs">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" aria-hidden="true" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search files..."
          aria-label="Search treemap nodes"
          className="w-full pl-9 pr-8 py-1.5 bg-slate-700 text-sm text-white rounded-md border border-slate-600
                     placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
        />
        {searchQuery && (
          <>
            <button
              onClick={() => onSearchChange('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-slate-400 hover:text-white transition-colors"
              aria-label="Clear search"
            >
              <X className="w-4 h-4" />
            </button>
            {matchCount !== undefined && (
              <span className="absolute right-8 top-1/2 -translate-y-1/2 text-xs text-slate-400">
                {matchCount} match{matchCount !== 1 ? 'es' : ''}
              </span>
            )}
          </>
        )}
      </div>

      {/* Zoom controls */}
      <div className="flex items-center gap-1 bg-slate-700 rounded-md p-1" role="group" aria-label="Zoom controls">
        <button
          onClick={onZoomOut}
          disabled={zoomLevel <= 0.5}
          className="p-1.5 rounded text-slate-300 hover:bg-slate-600 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          aria-label="Zoom out"
          title="Zoom out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>

        <span className="px-2 text-xs text-slate-300 min-w-[3rem] text-center" aria-live="polite">
          {Math.round(zoomLevel * 100)}%
        </span>

        <button
          onClick={onZoomIn}
          disabled={zoomLevel >= 4}
          className="p-1.5 rounded text-slate-300 hover:bg-slate-600 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          aria-label="Zoom in"
          title="Zoom in"
        >
          <ZoomIn className="w-4 h-4" />
        </button>

        <div className="w-px h-4 bg-slate-600 mx-1" />

        <button
          onClick={onResetZoom}
          className="p-1.5 rounded text-slate-300 hover:bg-slate-600 hover:text-white transition-colors"
          aria-label="Reset zoom and position"
          title="Reset view"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

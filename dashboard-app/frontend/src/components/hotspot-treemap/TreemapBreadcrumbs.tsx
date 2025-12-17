import { ChevronRight, Home } from 'lucide-react'

export interface BreadcrumbItem {
  name: string
  path: string
}

interface TreemapBreadcrumbsProps {
  items: BreadcrumbItem[]
  onNavigate: (path: string | null) => void
}

export default function TreemapBreadcrumbs({ items, onNavigate }: TreemapBreadcrumbsProps) {
  if (items.length === 0) return null

  return (
    <nav aria-label="Treemap navigation breadcrumbs" className="mb-3">
      <ol className="flex items-center gap-1 text-sm flex-wrap" role="list">
        {/* Root/Home */}
        <li className="flex items-center">
          <button
            onClick={() => onNavigate(null)}
            className="flex items-center gap-1 px-2 py-1 rounded text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
            aria-label="Go to root"
          >
            <Home className="w-3.5 h-3.5" aria-hidden="true" />
            <span className="sr-only sm:not-sr-only">Root</span>
          </button>
        </li>

        {items.map((item, index) => {
          const isLast = index === items.length - 1
          return (
            <li key={item.path} className="flex items-center">
              <ChevronRight className="w-4 h-4 text-slate-500 mx-0.5" aria-hidden="true" />
              {isLast ? (
                <span
                  className="px-2 py-1 rounded bg-cyan-500/20 text-cyan-300 font-medium"
                  aria-current="location"
                >
                  {item.name}
                </span>
              ) : (
                <button
                  onClick={() => onNavigate(item.path)}
                  className="px-2 py-1 rounded text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
                >
                  {item.name}
                </button>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

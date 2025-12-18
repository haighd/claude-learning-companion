import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { Command, Sparkles, Home, Brain, Play, Clock, Search, BarChart3, Network, MessageSquare, Lightbulb, FileWarning, Shield, AlertTriangle } from 'lucide-react'
import { ConnectionStatus, CeoInboxDropdown, CeoItemModal, CeoItem } from './header-components'
import { SettingsPanel } from './SettingsPanel'
import { TabId, MAIN_TABS, ADVANCED_TABS, getPathFromTab } from '../router'

interface HeaderProps {
  isConnected: boolean
  onOpenCommandPalette?: () => void
  activeTab?: TabId
  onTabChange?: (tab: TabId) => void
}

// Map tab IDs to icons
const TAB_ICONS: Record<TabId, typeof Home> = {
  overview: Home,
  heuristics: Brain,
  runs: Play,
  sessions: MessageSquare,
  analytics: BarChart3,
  graph: Network,
  timeline: Clock,
  query: Search,
  assumptions: Lightbulb,
  spikes: FileWarning,
  invariants: Shield,
  fraud: AlertTriangle,
}

export default function Header({ isConnected, onOpenCommandPalette, activeTab = 'overview', onTabChange }: HeaderProps) {
  const [ceoItems, setCeoItems] = useState<CeoItem[]>([])
  const [showCeoDropdown, setShowCeoDropdown] = useState(false)
  const [selectedItem, setSelectedItem] = useState<CeoItem | null>(null)
  const [itemContent, setItemContent] = useState<string>('')
  const [loadingContent, setLoadingContent] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  // Fetch CEO inbox items
  useEffect(() => {
    const fetchCeoInbox = async () => {
      try {
        const res = await fetch('/api/ceo-inbox')
        if (res.ok) {
          const data = await res.json()
          setCeoItems(data)
        }
      } catch (e) {
        console.error('Failed to fetch CEO inbox:', e)
      }
    }
    fetchCeoInbox()
    const interval = setInterval(fetchCeoInbox, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleItemClick = async (item: CeoItem) => {
    setSelectedItem(item)
    setLoadingContent(true)
    try {
      const res = await fetch(`/api/ceo-inbox/${item.filename}`)
      if (res.ok) {
        const data = await res.json()
        setItemContent(data.content)
      }
    } catch (e) {
      console.error('Failed to fetch item content:', e)
      setItemContent('Failed to load content')
    }
    setLoadingContent(false)
  }

  const closeModal = () => {
    setSelectedItem(null)
    setItemContent('')
  }

  return (
    <>
      <header className="sticky top-2 z-50 pointer-events-none transition-all duration-300 bg-transparent">
        {/* Pointer events on header container are none so clicks pass through to canvas on sides, 
            but we re-enable them on the actual content */}

        {/* Unified Pill Container */}
        <div className="container mx-auto px-4 flex justify-center pointer-events-auto">
          <div className="glass-panel border border-white/10 rounded-[2rem] shadow-2xl bg-black/60 backdrop-blur-xl flex flex-col md:flex-row items-center p-2 gap-4 md:gap-8 min-w-[320px] max-w-full">

            {/* Left Side: Brand */}
            <div className="flex items-center gap-4 px-4 shrink-0">
              {/* Logo & Brand */}
              <div className="flex items-center gap-3 shrink-0">
                <div className="relative">
                  <Sparkles className="w-6 h-6 text-cyan-400" />
                  <div className="absolute inset-0 blur-lg bg-cyan-500/30 animate-pulse" />
                </div>
                <div>
                  <h1 className="text-sm font-bold tracking-tight bg-gradient-to-r from-white via-cyan-200 to-cyan-400 bg-clip-text text-transparent">
                    CLC
                  </h1>
                  <p className="text-[8px] text-white/40 tracking-[0.2em] uppercase -mt-0.5">
                    LEARNING COMPANION
                  </p>
                </div>
              </div>

              {/* Command Palette Button */}
              <button
                onClick={() => {
                  if (onOpenCommandPalette) onOpenCommandPalette();
                }}
                className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-full hover:bg-white/10 transition-all text-white/40 hover:text-white/70
                           focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                aria-label="Open command palette (Cmd+K)"
                aria-keyshortcuts="Meta+K"
              >
                <Command className="w-4 h-4" aria-hidden="true" />
                <span className="text-xs">⌘K</span>
              </button>
            </div>

            {/* Center: Tab Navigation */}
            <div className="flex-1 flex justify-center">
              <nav className="flex items-center gap-1" role="navigation" aria-label="Dashboard navigation">
                {MAIN_TABS.map(({ id, label, path }) => {
                  const Icon = TAB_ICONS[id]
                  return (
                    <NavLink
                      key={id}
                      to={path}
                      end={id === 'overview'}
                      className={({ isActive }) =>
                        `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all
                         focus:outline-none focus:ring-2 focus:ring-cyan-500/50 ${
                          isActive
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                            : 'text-white/50 hover:text-white/80 hover:bg-white/5'
                        }`
                      }
                    >
                      <Icon className="w-3.5 h-3.5" aria-hidden="true" />
                      <span className="hidden lg:inline">{label}</span>
                      <span className="lg:hidden sr-only">{label}</span>
                    </NavLink>
                  )
                })}

                {/* Advanced tabs dropdown */}
                <div className="relative">
                  <button
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    aria-expanded={showAdvanced}
                    aria-haspopup="menu"
                    aria-label="More navigation options"
                    className={`flex items-center gap-1 px-2 py-1.5 rounded-full text-xs transition-all
                               focus:outline-none focus:ring-2 focus:ring-cyan-500/50 ${
                      ADVANCED_TABS.some(t => t.id === activeTab)
                        ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
                        : 'text-white/50 hover:text-white/80 hover:bg-white/5'
                    }`}
                  >
                    <span>More</span>
                    <span className="text-[10px]" aria-hidden="true">▾</span>
                  </button>

                  {showAdvanced && (
                    <div
                      className="absolute top-full mt-2 right-0 bg-black/90 backdrop-blur-xl border border-white/10 rounded-lg shadow-xl p-1 min-w-[140px] z-50"
                      role="menu"
                      aria-label="Advanced navigation options"
                    >
                      {ADVANCED_TABS.map(({ id, label, path }) => {
                        const Icon = TAB_ICONS[id]
                        return (
                          <NavLink
                            key={id}
                            to={path}
                            role="menuitem"
                            onClick={() => setShowAdvanced(false)}
                            className={({ isActive }) =>
                              `w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-all
                               focus:outline-none focus:ring-2 focus:ring-violet-500/50 ${
                                isActive
                                  ? 'bg-violet-500/20 text-violet-300'
                                  : 'text-white/60 hover:text-white hover:bg-white/5'
                              }`
                            }
                          >
                            <Icon className="w-3.5 h-3.5" aria-hidden="true" />
                            {label}
                          </NavLink>
                        )
                      })}
                    </div>
                  )}
                </div>
              </nav>
            </div>

            {/* Right Side: Actions */}
            <div className="flex items-center gap-3 px-3 border-l border-white/5 shrink-0">
              <CeoInboxDropdown
                items={ceoItems}
                isOpen={showCeoDropdown}
                onToggle={() => setShowCeoDropdown(!showCeoDropdown)}
                onClose={() => setShowCeoDropdown(false)}
                onItemClick={handleItemClick}
              />

              <SettingsPanel />

              <div className="w-px h-6 bg-white/10 mx-1" />
              <ConnectionStatus isConnected={isConnected} />
            </div>
          </div>
        </div>
      </header>

      {/* CEO Item Detail Modal */}
      {
        selectedItem && (
          <CeoItemModal
            item={selectedItem}
            content={itemContent}
            loading={loadingContent}
            onClose={closeModal}
          />
        )
      }
    </>
  )
}

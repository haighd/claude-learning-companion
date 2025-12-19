export type TabId = 'overview' | 'heuristics' | 'runs' | 'timeline' | 'query' | 'analytics' | 'graph' | 'sessions' | 'workflows' | 'assumptions' | 'spikes' | 'invariants' | 'fraud'

export interface TabRoute {
  id: TabId
  path: string
  label: string
}

export const TAB_ROUTES: TabRoute[] = [
  { id: 'overview', path: '/', label: 'Overview' },
  { id: 'heuristics', path: '/heuristics', label: 'Heuristics' },
  { id: 'runs', path: '/runs', label: 'Runs' },
  { id: 'sessions', path: '/sessions', label: 'Sessions' },
  { id: 'workflows', path: '/workflows', label: 'Workflows' },
  { id: 'analytics', path: '/analytics', label: 'Analytics' },
  { id: 'graph', path: '/graph', label: 'Graph' },
  { id: 'timeline', path: '/timeline', label: 'Timeline' },
  { id: 'query', path: '/query', label: 'Query' },
  { id: 'assumptions', path: '/assumptions', label: 'Assumptions' },
  { id: 'spikes', path: '/spikes', label: 'Spikes' },
  { id: 'invariants', path: '/invariants', label: 'Invariants' },
  { id: 'fraud', path: '/fraud', label: 'Fraud' },
]

export const MAIN_TABS: TabRoute[] = TAB_ROUTES.slice(0, 9)  // Include workflows
export const ADVANCED_TABS: TabRoute[] = TAB_ROUTES.slice(9)

export const getTabFromPath = (pathname: string): TabId => {
  // Handle trailing slashes
  const normalizedPath = pathname === '/' ? '/' : pathname.replace(/\/$/, '')
  const route = TAB_ROUTES.find(r => r.path === normalizedPath)
  return route?.id ?? 'overview'
}

export const getPathFromTab = (tabId: TabId): string => {
  const route = TAB_ROUTES.find(r => r.id === tabId)
  return route?.path ?? '/'
}

export const isAdvancedTab = (tabId: TabId): boolean => {
  return ADVANCED_TABS.some(t => t.id === tabId)
}

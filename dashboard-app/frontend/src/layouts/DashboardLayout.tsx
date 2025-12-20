import React from 'react'
import Header from '../components/Header'
import { NotificationPanel } from '../components/NotificationPanel'
import { CommandPalette } from '../components/CommandPalette'
import { LearningVelocity } from '../components/learning-velocity'
import { KnowledgeGraph } from '../components'
import { useNotificationContext } from '../context/NotificationContext'

interface DashboardLayoutProps {
    children: React.ReactNode
    activeTab: string
    isConnected: boolean
    commandPaletteOpen: boolean
    setCommandPaletteOpen: (open: boolean) => void
    commands: any[]
    onDomainSelect?: (domain: string) => void
    onTabChange?: (tab: string) => void
    selectedDomain?: string | null
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
    children,
    activeTab,
    isConnected,
    commandPaletteOpen,
    setCommandPaletteOpen,
    commands,
    onDomainSelect,
    onTabChange,
    selectedDomain
}) => {
    const notifications = useNotificationContext()

    return (
        <div className="min-h-screen relative transition-colors duration-300 bg-[var(--theme-bg-primary)]">
            {/* Skip link for keyboard users */}
            <a
                href="#main-content"
                className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-[var(--theme-accent)] focus:text-[var(--theme-bg-primary)] focus:rounded-lg focus:font-medium focus:shadow-lg"
            >
                Skip to main content
            </a>

            <CommandPalette
                isOpen={commandPaletteOpen}
                onClose={() => setCommandPaletteOpen(false)}
                commands={commands}
            />

            <NotificationPanel
                notifications={notifications.notifications}
                onDismiss={notifications.removeNotification}
                onClearAll={notifications.clearAll}
                soundEnabled={notifications.soundEnabled}
                onToggleSound={notifications.toggleSound}
            />

            <Header
                isConnected={isConnected}
                onOpenCommandPalette={() => setCommandPaletteOpen(true)}
                activeTab={activeTab as any}
                onTabChange={onTabChange as any}
            />

            <main id="main-content" className="w-full" tabIndex={-1}>
                {/* Overview Tab - Stats + Runs */}
                {activeTab === 'overview' && (
                    <div className="container mx-auto px-4 py-2">
                        {children}
                    </div>
                )}

                {/* Knowledge Graph View */}
                {activeTab === 'graph' && (
                    <div className="container mx-auto px-4 py-2">
                        <KnowledgeGraph
                            onNodeClick={(node) => {
                                if (onDomainSelect && node.domain) onDomainSelect(node.domain);
                            }}
                        />
                    </div>
                )}

                {/* Analytics View */}
                {activeTab === 'analytics' && (
                    <div className="container mx-auto px-4 py-2">
                        <LearningVelocity days={30} />
                    </div>
                )}

                {/* Other tabs */}
                {activeTab !== 'overview' && activeTab !== 'graph' && activeTab !== 'analytics' && (
                    <div className="container mx-auto px-4 py-2">
                        <div className="bg-[var(--theme-bg-secondary)] border border-[var(--theme-border)] p-4 rounded-lg min-h-[calc(100vh-100px)] max-h-[calc(100vh-100px)] overflow-y-auto">
                            {children}
                        </div>
                    </div>
                )}
            </main>
        </div>
    )
}

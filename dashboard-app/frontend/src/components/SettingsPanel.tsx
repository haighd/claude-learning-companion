import { useState } from 'react'
import { createPortal } from 'react-dom'
import { Settings, X, Moon, Sun } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTheme, Theme } from '../context'

export function SettingsPanel() {
  const [isOpen, setIsOpen] = useState(false)
  const { theme, setTheme } = useTheme()

  const themes: { id: Theme; name: string; icon: any }[] = [
    { id: 'black-hole', name: 'Dark', icon: Moon },
    { id: 'white-dwarf', name: 'Light', icon: Sun },
  ]

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="p-2 rounded-full bg-[var(--theme-bg-secondary)] hover:bg-[var(--theme-bg-tertiary)] transition-colors border border-[var(--theme-border)]"
        style={{ color: 'var(--theme-text-primary)' }}
        title="Settings"
      >
        <Settings className="w-5 h-5" />
      </button>

      {createPortal(
        <AnimatePresence>
          {isOpen && (
            <>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setIsOpen(false)}
                className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[9999]"
              />
              <motion.div
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                className="fixed inset-y-0 right-0 z-[10002] w-80 p-6 overflow-y-auto border-l shadow-2xl"
                style={{
                  backgroundColor: 'var(--theme-bg-primary)',
                  borderColor: 'var(--theme-border)'
                }}
              >
                <div className="flex items-center justify-between mb-8">
                  <h2 className="text-xl font-bold flex items-center gap-2" style={{ color: 'var(--theme-text-primary)' }}>
                    <Settings className="w-5 h-5" style={{ color: 'var(--theme-accent)' }} />
                    Settings
                  </h2>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-1 transition-colors hover:opacity-70"
                    style={{ color: 'var(--theme-text-secondary)' }}
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium mb-3" style={{ color: 'var(--theme-text-secondary)' }}>
                      Theme
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      {themes.map((t) => (
                        <button
                          key={t.id}
                          onClick={() => setTheme(t.id)}
                          className={
                            'flex items-center gap-2 p-3 rounded-lg border transition-all ' +
                            (theme === t.id
                              ? 'border-[var(--theme-accent)] bg-[var(--theme-bg-secondary)]'
                              : 'border-[var(--theme-border)] hover:border-[var(--theme-text-secondary)]')
                          }
                        >
                          <t.icon className="w-4 h-4" style={{ color: 'var(--theme-accent)' }} />
                          <div className="text-left">
                            <span className="text-sm font-medium block" style={{ color: 'var(--theme-text-primary)' }}>
                              {t.name}
                            </span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="pt-4 border-t" style={{ borderColor: 'var(--theme-border)' }}>
                    <p className="text-xs" style={{ color: 'var(--theme-text-secondary)' }}>
                      Settings are saved automatically.
                    </p>
                  </div>
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>,
        document.body
      )}
    </>
  )
}

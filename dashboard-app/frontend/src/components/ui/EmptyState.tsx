import React from 'react';

type EmptyStateVariant = 'default' | 'search' | 'error' | 'no-data' | 'filtered';

interface EmptyStateProps {
  variant?: EmptyStateVariant;
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

const defaultContent: Record<EmptyStateVariant, { title: string; description: string; icon: string }> = {
  default: {
    title: 'Nothing here yet',
    description: 'Data will appear here once available.',
    icon: '📭',
  },
  search: {
    title: 'No results found',
    description: 'Try adjusting your search terms or filters.',
    icon: '🔍',
  },
  error: {
    title: 'Something went wrong',
    description: 'We encountered an error loading this data.',
    icon: '⚠️',
  },
  'no-data': {
    title: 'No data available',
    description: 'There is no data to display at this time.',
    icon: '📊',
  },
  filtered: {
    title: 'No matching items',
    description: 'No items match your current filters.',
    icon: '🔎',
  },
};

export const EmptyState: React.FC<EmptyStateProps> = ({
  variant = 'default',
  title,
  description,
  icon,
  action,
  className = '',
}) => {
  const content = defaultContent[variant];

  return (
    <div
      className={`flex flex-col items-center justify-center py-12 px-6 text-center ${className}`}
      role="status"
      aria-label={title || content.title}
    >
      <div
        className="text-5xl mb-4 opacity-60"
        aria-hidden="true"
      >
        {icon || content.icon}
      </div>

      <h3 className="text-heading-3 text-[var(--theme-text-primary)] mb-2">
        {title || content.title}
      </h3>

      <p className="text-body text-[var(--theme-text-secondary)] max-w-md mb-6">
        {description || content.description}
      </p>

      {action && (
        <button
          onClick={action.onClick}
          className="px-6 py-2.5 rounded-[var(--radius-md)]
                     bg-[var(--theme-accent)] text-[var(--theme-bg-primary)]
                     font-medium transition-all duration-[var(--duration-normal)]
                     hover:shadow-[var(--shadow-glow)] hover:scale-105
                     focus:outline-none focus:ring-2 focus:ring-[var(--theme-accent)] focus:ring-offset-2 focus:ring-offset-[var(--theme-bg-primary)]"
          type="button"
        >
          {action.label}
        </button>
      )}
    </div>
  );
};

interface EmptyStateWithIllustrationProps extends Omit<EmptyStateProps, 'icon'> {
  illustration: 'chart' | 'list' | 'search' | 'error' | 'success';
}

const illustrations: Record<string, React.ReactNode> = {
  chart: (
    <svg className="w-24 h-24 text-[var(--theme-accent)]" viewBox="0 0 100 100" fill="none" aria-hidden="true">
      <rect x="10" y="60" width="15" height="30" rx="2" fill="currentColor" opacity="0.3" />
      <rect x="30" y="40" width="15" height="50" rx="2" fill="currentColor" opacity="0.5" />
      <rect x="50" y="50" width="15" height="40" rx="2" fill="currentColor" opacity="0.4" />
      <rect x="70" y="20" width="15" height="70" rx="2" fill="currentColor" opacity="0.6" />
      <line x1="5" y1="90" x2="95" y2="90" stroke="currentColor" strokeWidth="2" opacity="0.3" />
    </svg>
  ),
  list: (
    <svg className="w-24 h-24 text-[var(--theme-accent)]" viewBox="0 0 100 100" fill="none" aria-hidden="true">
      <rect x="10" y="20" width="80" height="12" rx="2" fill="currentColor" opacity="0.2" />
      <rect x="10" y="40" width="60" height="12" rx="2" fill="currentColor" opacity="0.3" />
      <rect x="10" y="60" width="70" height="12" rx="2" fill="currentColor" opacity="0.2" />
      <rect x="10" y="80" width="50" height="12" rx="2" fill="currentColor" opacity="0.15" />
    </svg>
  ),
  search: (
    <svg className="w-24 h-24 text-[var(--theme-accent)]" viewBox="0 0 100 100" fill="none" aria-hidden="true">
      <circle cx="42" cy="42" r="25" stroke="currentColor" strokeWidth="4" opacity="0.4" />
      <line x1="60" y1="60" x2="85" y2="85" stroke="currentColor" strokeWidth="4" strokeLinecap="round" opacity="0.4" />
      <path d="M35 42 L42 49 L55 36" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" opacity="0.6" />
    </svg>
  ),
  error: (
    <svg className="w-24 h-24 text-[var(--neon-amber)]" viewBox="0 0 100 100" fill="none" aria-hidden="true">
      <circle cx="50" cy="50" r="40" stroke="currentColor" strokeWidth="4" opacity="0.3" />
      <line x1="50" y1="30" x2="50" y2="55" stroke="currentColor" strokeWidth="4" strokeLinecap="round" opacity="0.6" />
      <circle cx="50" cy="68" r="3" fill="currentColor" opacity="0.6" />
    </svg>
  ),
  success: (
    <svg className="w-24 h-24 text-emerald-400" viewBox="0 0 100 100" fill="none" aria-hidden="true">
      <circle cx="50" cy="50" r="40" stroke="currentColor" strokeWidth="4" opacity="0.3" />
      <path d="M30 50 L45 65 L70 35" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" opacity="0.6" />
    </svg>
  ),
};

export const EmptyStateWithIllustration: React.FC<EmptyStateWithIllustrationProps> = ({
  illustration,
  ...props
}) => {
  return (
    <EmptyState
      {...props}
      icon={illustrations[illustration]}
    />
  );
};

export default EmptyState;

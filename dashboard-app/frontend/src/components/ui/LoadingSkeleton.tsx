import React from 'react';

interface LoadingSkeletonProps {
  variant?: 'text' | 'circular' | 'rectangular' | 'card' | 'stat';
  width?: string | number;
  height?: string | number;
  className?: string;
  lines?: number;
  animate?: boolean;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  variant = 'rectangular',
  width,
  height,
  className = '',
  lines = 1,
  animate = true,
}) => {
  const baseClasses = `bg-[rgba(var(--theme-panel-rgb),0.3)] ${animate ? 'skeleton-shimmer' : ''}`;

  const getVariantClasses = () => {
    switch (variant) {
      case 'text':
        return 'h-4 rounded';
      case 'circular':
        return 'rounded-full';
      case 'rectangular':
        return 'rounded-[var(--radius-md)]';
      case 'card':
        return 'rounded-[var(--radius-lg)] min-h-[120px]';
      case 'stat':
        return 'rounded-[var(--radius-md)] h-20';
      default:
        return 'rounded-[var(--radius-md)]';
    }
  };

  const style: React.CSSProperties = {
    width: width ?? (variant === 'circular' ? '40px' : '100%'),
    height: height ?? (variant === 'circular' ? '40px' : undefined),
  };

  if (variant === 'text' && lines > 1) {
    return (
      <div className={`space-y-2 ${className}`} role="status" aria-label="Loading">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={`${baseClasses} ${getVariantClasses()}`}
            style={{
              ...style,
              width: i === lines - 1 ? '75%' : style.width,
            }}
          />
        ))}
        <span className="sr-only">Loading...</span>
      </div>
    );
  }

  return (
    <div
      className={`${baseClasses} ${getVariantClasses()} ${className}`}
      style={style}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
};

interface SkeletonGroupProps {
  children: React.ReactNode;
  className?: string;
}

export const SkeletonGroup: React.FC<SkeletonGroupProps> = ({ children, className = '' }) => (
  <div className={`animate-pulse ${className}`} role="status" aria-busy="true">
    {children}
    <span className="sr-only">Loading content...</span>
  </div>
);

export const StatsSkeleton: React.FC = () => (
  <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-4" role="status" aria-label="Loading statistics">
    {Array.from({ length: 8 }).map((_, i) => (
      <div key={i} className="glass-panel p-4 rounded-[var(--radius-lg)]">
        <LoadingSkeleton variant="text" width="60%" className="mb-2" />
        <LoadingSkeleton variant="text" height="2rem" width="80%" />
      </div>
    ))}
    <span className="sr-only">Loading statistics...</span>
  </div>
);

export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => (
  <div className="space-y-2" role="status" aria-label="Loading table">
    <LoadingSkeleton height="40px" className="mb-4" />
    {Array.from({ length: rows }).map((_, i) => (
      <LoadingSkeleton key={i} height="48px" />
    ))}
    <span className="sr-only">Loading table data...</span>
  </div>
);

export const CardSkeleton: React.FC = () => (
  <div className="glass-panel p-6 rounded-[var(--radius-lg)]" role="status" aria-label="Loading card">
    <div className="flex items-center gap-4 mb-4">
      <LoadingSkeleton variant="circular" width={48} height={48} />
      <div className="flex-1">
        <LoadingSkeleton variant="text" width="40%" className="mb-2" />
        <LoadingSkeleton variant="text" width="60%" />
      </div>
    </div>
    <LoadingSkeleton variant="text" lines={3} />
    <span className="sr-only">Loading card content...</span>
  </div>
);

export default LoadingSkeleton;

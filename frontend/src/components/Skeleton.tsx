export default function Skeleton({ className = "" }: { className?: string }) {
  return <span className={`skeleton-pulse inline-block rounded bg-border ${className}`} aria-hidden="true" />;
}

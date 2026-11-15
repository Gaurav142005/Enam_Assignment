/** Re-mounts on every navigation, so each page settles in with a short rise instead of snapping. */
export default function Template({ children }: { children: React.ReactNode }) {
  return <div className="animate-rise motion-reduce:animate-none">{children}</div>;
}

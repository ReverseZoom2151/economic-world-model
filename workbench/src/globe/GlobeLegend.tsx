interface GlobeLegendProps {
  readonly activeCount: number;
  readonly comparisonCount: number;
  readonly flowCount: number;
  readonly uncertaintyLabel: string;
}

export function GlobeLegend({
  activeCount,
  comparisonCount,
  flowCount,
  uncertaintyLabel,
}: GlobeLegendProps) {
  return (
    <section className="globe-legend" aria-label="Economic globe legend">
      <div><span className="globe-swatch globe-swatch--active" /><strong>{activeCount}</strong><span>active-run anchors</span></div>
      <div><span className="globe-swatch globe-swatch--comparison" /><strong>{comparisonCount}</strong><span>comparison anchors</span></div>
      <div><span className="globe-swatch globe-swatch--flow" /><strong>{flowCount}</strong><span>bounded typed relations</span></div>
      <div><strong>{uncertaintyLabel}</strong><span>declared coordinate uncertainty</span></div>
      <div><strong>Source</strong><span>researcher-declared coordinates only</span></div>
    </section>
  );
}

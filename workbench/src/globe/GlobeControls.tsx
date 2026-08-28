interface GlobeControlsProps {
  readonly kinds: ReadonlyArray<string>;
  readonly enabledKinds: ReadonlySet<string>;
  readonly showFlows: boolean;
  readonly showUncertainty: boolean;
  readonly onToggleKind: (kind: string) => void;
  readonly onShowFlows: (value: boolean) => void;
  readonly onShowUncertainty: (value: boolean) => void;
}

export function GlobeControls({
  kinds,
  enabledKinds,
  showFlows,
  showUncertainty,
  onToggleKind,
  onShowFlows,
  onShowUncertainty,
}: GlobeControlsProps) {
  return (
    <section className="globe-controls" aria-label="Globe display controls">
      <fieldset>
        <legend>Anchored object types</legend>
        <div className="globe-controls__options">
          {kinds.map((kind) => (
            <label key={kind}>
              <input
                type="checkbox"
                checked={enabledKinds.has(kind)}
                onChange={() => onToggleKind(kind)}
              />
              {kind.replaceAll("_", " ")}
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend>Evidence overlays</legend>
        <div className="globe-controls__options">
          <label>
            <input
              type="checkbox"
              checked={showFlows}
              onChange={(event) => onShowFlows(event.currentTarget.checked)}
            />
            Bounded relations
          </label>
          <label>
            <input
              type="checkbox"
              checked={showUncertainty}
              onChange={(event) => onShowUncertainty(event.currentTarget.checked)}
            />
            Uncertainty rings
          </label>
        </div>
      </fieldset>
    </section>
  );
}

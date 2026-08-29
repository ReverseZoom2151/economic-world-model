import type {
  MeasurementContract,
  OntologyObjectContract,
} from "../../data/InvestigationDataSource";
import { MarketCharts } from "../../visuals/market/MarketCharts";
import { marketMeasurementIssue } from "../../visuals/market/spec";
import { ontologyObjectLabel } from "../../visuals/shared/objectLabel";

interface MarketLensProps {
  readonly measurements: ReadonlyArray<MeasurementContract>;
  readonly rejections: ReadonlyArray<OntologyObjectContract>;
  readonly bounded?: boolean;
}

export function MarketLens({ measurements, rejections, bounded = false }: MarketLensProps) {
  const assessed = measurements.map((measurement) => ({
    measurement,
    issue: marketMeasurementIssue(measurement),
  }));
  const chartable = assessed
    .filter((entry) => entry.issue === null)
    .map((entry) => entry.measurement);
  const withheld = assessed.filter((entry) => entry.issue !== null);
  const explainedRejections = rejections.filter(
    (rejection) => typeof rejection.properties.reason === "string",
  ).length;
  return (
    <article className="lens-surface market-lens">
      <header className="lens-heading">
        <div>
          <p>Market / outcomes</p>
          <h2>Market outcomes</h2>
        </div>
        <strong>{rejections.length} rejected</strong>
      </header>
      <dl className="market-summary" aria-label="Loaded market outcome summary">
        <div><dt>Measurements</dt><dd>{measurements.length}</dd></div>
        <div><dt>Chart-ready</dt><dd>{chartable.length}</dd></div>
        <div><dt>Rejections</dt><dd>{rejections.length}</dd></div>
        <div><dt>Reasons recorded</dt><dd>{explainedRejections}</dd></div>
      </dl>
      {bounded ? (
        <p className="bounded-notice" role="status">Summary covers the loaded bounded page.</p>
      ) : null}
      {chartable.length === 0 ? (
        <p className="sparse-fallback">
          {measurements.length === 0
            ? "No market measurements were projected for this run."
            : "No market measurements include the metadata required for a scientific chart."}
        </p>
      ) : (
        <MarketCharts measurements={chartable} />
      )}
      {withheld.length > 0 ? (
        <aside className="withheld-records" aria-label="Withheld market measurements">
          <strong>{withheld.length} measurement records withheld</strong>
          <ul>
            {withheld.map(({ measurement, issue }) => (
              <li key={measurement.ref.id}>
                {measurement.name}: {issue}
              </li>
            ))}
          </ul>
        </aside>
      ) : null}
      <details className="rejection-ledger" open={rejections.length > 0 && rejections.length <= 8}>
        <summary id="market-rejections">Market rejections · {rejections.length}</summary>
        {rejections.length === 0 ? (
          <p>No rejected orders or settlements were projected.</p>
        ) : (
          <ul>
            {rejections.map((rejection) => (
              <li key={rejection.ref.id}>
                <strong>
                  {ontologyObjectLabel(rejection)}
                </strong>
                <span>
                  {typeof rejection.properties.reason === "string"
                    ? rejection.properties.reason
                    : "reason unavailable"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </details>
    </article>
  );
}

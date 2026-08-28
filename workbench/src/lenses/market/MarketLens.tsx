import type {
  MeasurementContract,
  OntologyObjectContract,
} from "../../data/InvestigationDataSource";
import { MarketCharts } from "../../visuals/market/MarketCharts";
import { marketMeasurementIssue } from "../../visuals/market/spec";

interface MarketLensProps {
  readonly measurements: ReadonlyArray<MeasurementContract>;
  readonly rejections: ReadonlyArray<OntologyObjectContract>;
}

export function MarketLens({ measurements, rejections }: MarketLensProps) {
  const assessed = measurements.map((measurement) => ({
    measurement,
    issue: marketMeasurementIssue(measurement),
  }));
  const chartable = assessed
    .filter((entry) => entry.issue === null)
    .map((entry) => entry.measurement);
  const withheld = assessed.filter((entry) => entry.issue !== null);
  return (
    <article className="lens-surface market-lens">
      <header className="lens-heading">
        <div>
          <p>Market / outcomes</p>
          <h2>Market outcomes</h2>
        </div>
        <strong>{rejections.length} rejected</strong>
      </header>
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
      <section className="rejection-ledger" aria-labelledby="market-rejections">
        <h3 id="market-rejections">Market rejections</h3>
        {rejections.length === 0 ? (
          <p>No rejected orders or settlements were projected.</p>
        ) : (
          <ul>
            {rejections.map((rejection) => (
              <li key={rejection.ref.id}>
                <strong>
                  {typeof rejection.properties.natural_key === "string"
                    ? rejection.properties.natural_key
                    : rejection.ref.id}
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
      </section>
    </article>
  );
}

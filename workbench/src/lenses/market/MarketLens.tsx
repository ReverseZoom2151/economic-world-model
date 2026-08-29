import type {
  MeasurementContract,
  OntologyObjectContract,
} from "../../data/InvestigationDataSource";
import { MarketCharts } from "../../visuals/market/MarketCharts";
import {
  marketMeasurementIssue,
  sampleSize,
  sourceLabel,
} from "../../visuals/market/spec";
import { TechnicalDetails } from "../../visuals/provenance/TechnicalDetails";
import { ontologyObjectLabel } from "../../visuals/shared/objectLabel";

interface MarketLensProps {
  readonly measurements: ReadonlyArray<MeasurementContract>;
  readonly rejections: ReadonlyArray<OntologyObjectContract>;
  readonly bounded?: boolean;
}

function measurementName(name: string): string {
  return name
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function measurementValue(value: unknown): string {
  if (typeof value !== "number") return String(value);
  const magnitude = Math.abs(value);
  if (Number.isInteger(value)) return value.toLocaleString("en-US");
  if (magnitude > 0 && magnitude < 0.0001) return value.toExponential(2);
  if (magnitude < 0.01) return value.toFixed(4);
  return value.toLocaleString("en-US", { maximumFractionDigits: 5 });
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
  const rejectionChecks = rejections.filter((rejection) => rejection.ref.kind === "outcome");
  const actualRejections = rejections.filter((rejection) =>
    rejection.ref.kind === "market_rejection"
    || (typeof rejection.properties.rejected_count === "number"
      && rejection.properties.rejected_count > 0),
  );
  const rejectedMeasurement = measurements.find((measurement) => measurement.name === "rejected_orders");
  const rejectedOrders = typeof rejectedMeasurement?.value === "number"
    ? rejectedMeasurement.value
    : actualRejections.reduce((total, rejection) => {
        const count = rejection.properties.rejected_count;
        return total + (typeof count === "number" ? count : 1);
      }, 0);
  return (
    <article className="lens-surface market-lens">
      <header className="lens-heading">
        <div>
          <p>Market / outcomes</p>
          <h2>Market outcomes</h2>
        </div>
        <strong>{rejectedOrders.toLocaleString("en-US")} rejected</strong>
      </header>
      <dl className="market-summary" aria-label="Loaded market outcome summary">
        <div><dt>Measurements</dt><dd>{measurements.length}</dd></div>
        <div><dt>Chart-ready</dt><dd>{chartable.length}</dd></div>
        <div><dt>Rejected orders</dt><dd>{rejectedOrders.toLocaleString("en-US")}</dd></div>
        <div><dt>Checks loaded</dt><dd>{rejectionChecks.length}</dd></div>
      </dl>
      {measurements.length > 0 ? (
        <section className="market-metrics" aria-labelledby="market-metrics-title">
          <header>
            <p>Observed scalars</p>
            <h3 id="market-metrics-title">What this run measured</h3>
          </header>
          <div className="market-metrics__grid">
            {measurements.map((measurement) => (
              <article key={measurement.ref.id}>
                <span>{measurementName(measurement.name)}</span>
                <strong>{measurementValue(measurement.value)}</strong>
                <small>
                  {measurement.unit === "1" ? "dimensionless" : measurement.unit}
                  {` · n = ${sampleSize(measurement.sample)}`}
                </small>
                <TechnicalDetails
                  details={[
                    { label: "Record ID", value: measurement.ref.id },
                    { label: "Status", value: measurement.status },
                    { label: "Source", value: sourceLabel(measurement) },
                  ]}
                />
              </article>
            ))}
          </div>
        </section>
      ) : null}
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
      <details className="rejection-ledger" open={actualRejections.length > 0 && actualRejections.length <= 8}>
        <summary id="market-rejections">Rejected order ledger · {actualRejections.length}</summary>
        {actualRejections.length === 0 ? (
          <p>
            No rejected orders or settlements were projected. {rejectionChecks.length} loaded
            outcome checks reported zero rejections.
          </p>
        ) : (
          <ul>
            {actualRejections.map((rejection) => (
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

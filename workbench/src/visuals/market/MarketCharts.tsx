import type { Result } from "vega-embed";
import { useEffect, useMemo, useRef } from "react";

import type { MeasurementContract } from "../../data/InvestigationDataSource";
import { buildMarketSpec, sampleSize, sourceLabel, uncertaintyLabel } from "./spec";

interface MarketChartsProps {
  readonly measurements: ReadonlyArray<MeasurementContract>;
}

export function MarketCharts({ measurements }: MarketChartsProps) {
  const container = useRef<HTMLDivElement>(null);
  const spec = useMemo(() => buildMarketSpec(measurements), [measurements]);

  useEffect(() => {
    let result: Result | null = null;
    let active = true;
    if (
      container.current !== null &&
      typeof window.matchMedia === "function" &&
      !navigator.userAgent.toLowerCase().includes("jsdom")
    ) {
      const target = container.current;
      void import("vega-embed").then(({ default: embed }) =>
        embed(target, spec, {
          actions: false,
          renderer: "svg",
          tooltip: false,
        }).then((value) => {
          if (active) {
            result = value;
          } else {
            value.finalize();
          }
        }),
      );
    }
    return () => {
      active = false;
      result?.finalize();
    };
  }, [spec]);

  return (
    <figure className="market-chart" data-testid="market-chart">
      <div ref={container} aria-hidden="true" />
      <figcaption>Observed market measurements, separated by declared unit.</figcaption>
      <table>
        <thead>
          <tr>
            <th scope="col">Measurement</th>
            <th scope="col">Value</th>
            <th scope="col">Sample</th>
            <th scope="col">Uncertainty</th>
            <th scope="col">Source</th>
          </tr>
        </thead>
        <tbody>
          {measurements.map((measurement) => (
            <tr key={measurement.ref.id}>
              <th scope="row">{measurement.name}</th>
              <td>
                {String(measurement.value)} <span>{measurement.unit}</span>
              </td>
              <td>n = {sampleSize(measurement.sample)}</td>
              <td>{uncertaintyLabel(measurement.uncertainty)}</td>
              <td>{sourceLabel(measurement)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

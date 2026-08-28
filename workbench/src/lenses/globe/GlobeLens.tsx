import { lazy, Suspense, useEffect, useMemo, useState } from "react";

import type {
  InvestigationDataSource,
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import { GlobeLedger } from "../../globe/GlobeLedger";
import { GlobeLegend } from "../../globe/GlobeLegend";
import {
  boundedGeoFlows,
  eligibleGeoPlacements,
  type TaggedGeoPlacement,
} from "../../globe/geometry";
import { supportsWebGL } from "../../scene/capabilities";
import { SceneErrorBoundary } from "../../scene/SceneErrorBoundary";

const LazyEconomicGlobe = lazy(() =>
  import("../../globe/rendering/EconomicGlobe").then((module) => ({ default: module.EconomicGlobe })),
);

interface GlobeLensProps {
  readonly dataSource: InvestigationDataSource;
  readonly runId: string;
  readonly comparisonRunId: string | null;
  readonly selectedId: string | null;
  readonly time: number | null;
  readonly onSelect: (id: string) => void;
  readonly webglAvailable?: () => boolean;
}

interface RunRecords {
  readonly objects: ReadonlyArray<OntologyObjectContract>;
  readonly relations: ReadonlyArray<RelationContract>;
}

interface GlobeRecords {
  readonly key: string;
  readonly failed: boolean;
  readonly active: RunRecords;
  readonly comparison: RunRecords | null;
}

const EMPTY_RUN: RunRecords = { objects: [], relations: [] };

async function loadRun(dataSource: InvestigationDataSource, runId: string): Promise<RunRecords> {
  const [objects, relations] = await Promise.all([
    dataSource.objects({ runId, limit: 200 }),
    dataSource.relations({ runId, limit: 200 }),
  ]);
  return { objects: objects.items, relations: relations.items };
}

function tag(
  records: RunRecords,
  runId: string,
  runRole: TaggedGeoPlacement["runRole"],
  time: number | null,
): ReadonlyArray<TaggedGeoPlacement> {
  return eligibleGeoPlacements(records.objects, records.relations, time).map((placement) => ({
    ...placement,
    runId,
    runRole,
  }));
}

export function GlobeLens({
  dataSource,
  runId,
  comparisonRunId,
  selectedId,
  time,
  onSelect,
  webglAvailable = supportsWebGL,
}: GlobeLensProps) {
  const requestKey = `${runId}|${comparisonRunId ?? ""}`;
  const [records, setRecords] = useState<GlobeRecords>({
    key: "",
    failed: false,
    active: EMPTY_RUN,
    comparison: null,
  });

  useEffect(() => {
    let current = true;
    void Promise.all([
      loadRun(dataSource, runId),
      comparisonRunId === null ? Promise.resolve(null) : loadRun(dataSource, comparisonRunId),
    ])
      .then(([active, comparison]) => {
        if (current) setRecords({ key: requestKey, failed: false, active, comparison });
      })
      .catch(() => {
        if (current) {
          setRecords({ key: requestKey, failed: true, active: EMPTY_RUN, comparison: null });
        }
      });
    return () => {
      current = false;
    };
  }, [comparisonRunId, dataSource, requestKey, runId]);

  const activePlacements = useMemo(
    () => tag(records.active, runId, "active", time),
    [records.active, runId, time],
  );
  const comparisonPlacements = useMemo(
    () =>
      comparisonRunId === null || records.comparison === null
        ? []
        : tag(records.comparison, comparisonRunId, "comparison", time),
    [comparisonRunId, records.comparison, time],
  );
  const placements = useMemo(
    () => [...activePlacements, ...comparisonPlacements],
    [activePlacements, comparisonPlacements],
  );
  const flows = useMemo(
    () => [
      ...boundedGeoFlows(activePlacements, records.active.relations),
      ...boundedGeoFlows(comparisonPlacements, records.comparison?.relations ?? []),
    ],
    [activePlacements, comparisonPlacements, records.active.relations, records.comparison],
  );
  const available = useMemo(() => webglAvailable(), [webglAvailable]);

  return (
    <section className="analytical-lens globe-lens">
      <header className="analytical-lens__heading">
        <div>
          <p>10 / ECONOMIC GLOBE</p>
          <h2>Explicit economic geography</h2>
        </div>
        <p>Only sourced GEO_ANCHORED_AT relations become positions. No jurisdiction is inferred.</p>
      </header>
      {comparisonRunId !== null ? <p className="comparison-note">Comparison overlay: {comparisonRunId}</p> : null}
      {records.key !== requestKey ? <p className="lens-loading">Loading explicit coordinate evidence…</p> : null}
      {records.key === requestKey && records.failed ? (
        <p className="sparse-fallback" role="alert">The geographic projection is unavailable.</p>
      ) : null}
      {records.key === requestKey && !records.failed && placements.length === 0 ? (
        <section className="globe-unavailable">
          <h3>No explicit geography is available.</h3>
          <p>No jurisdiction or coordinate was inferred.</p>
        </section>
      ) : null}
      {records.key === requestKey && !records.failed && placements.length > 0 ? (
        <>
          <GlobeLegend
            activeCount={activePlacements.length}
            comparisonCount={comparisonPlacements.length}
            flowCount={flows.length}
          />
          {available ? (
            <SceneErrorBoundary
              key={requestKey}
              fallback={
                <GlobeLedger
                  placements={placements}
                  flows={flows}
                  selectedId={selectedId}
                  onSelect={onSelect}
                  renderingUnavailable
                />
              }
            >
              <Suspense fallback={<p className="lens-loading">Loading bundled globe geometry…</p>}>
                <LazyEconomicGlobe
                  placements={placements}
                  flows={flows}
                  selectedId={selectedId}
                  onSelect={onSelect}
                />
              </Suspense>
            </SceneErrorBoundary>
          ) : null}
          <GlobeLedger
            placements={placements}
            flows={flows}
            selectedId={selectedId}
            onSelect={onSelect}
            renderingUnavailable={!available}
          />
        </>
      ) : null}
    </section>
  );
}

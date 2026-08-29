import { lazy, Suspense, useEffect, useMemo, useState } from "react";

import type {
  InvestigationDataSource,
  OntologyObjectContract,
  RelationContract,
} from "../../data/InvestigationDataSource";
import { GlobeLedger } from "../../globe/GlobeLedger";
import { GlobeLegend } from "../../globe/GlobeLegend";
import { GlobeControls } from "../../globe/GlobeControls";
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
  const [objects, anchorRelations] = await Promise.all([
    dataSource.objects({ runId, limit: 200 }),
    dataSource.relations({ runId, relationTypes: ["GEO_ANCHORED_AT"], limit: 200 }),
  ]);
  const anchoredIds = anchorRelations.items.map((relation) => relation.source.id);
  const incidentRelations = anchoredIds.length === 0
    ? null
    : await dataSource.relations({
        runId,
        incidentIds: anchoredIds,
        direction: "both",
        limit: 200,
      });
  const relations = new Map(
    [...anchorRelations.items, ...(incidentRelations?.items ?? [])]
      .map((relation) => [relation.ref.id, relation]),
  );
  return { objects: objects.items, relations: [...relations.values()] };
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
  const [disabledKinds, setDisabledKinds] = useState<ReadonlySet<string>>(new Set());
  const [showFlows, setShowFlows] = useState(true);
  const [showUncertainty, setShowUncertainty] = useState(true);

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
  const kinds = useMemo(
    () => [...new Set(placements.map((placement) => placement.subject.ref.kind))]
      .sort((left, right) => left.localeCompare(right)),
    [placements],
  );
  const effectiveKinds = useMemo(
    () => new Set(kinds.filter((kind) => !disabledKinds.has(kind))),
    [disabledKinds, kinds],
  );
  const visiblePlacements = useMemo(
    () => placements.filter((placement) => effectiveKinds.has(placement.subject.ref.kind)),
    [effectiveKinds, placements],
  );
  const flows = useMemo(
    () => [
      ...boundedGeoFlows(activePlacements, records.active.relations),
      ...boundedGeoFlows(comparisonPlacements, records.comparison?.relations ?? []),
    ],
    [activePlacements, comparisonPlacements, records.active.relations, records.comparison],
  );
  const available = useMemo(() => webglAvailable(), [webglAvailable]);
  const visibleIds = useMemo(
    () => new Set(visiblePlacements.map((placement) => `${placement.runId}:${placement.subject.ref.id}`)),
    [visiblePlacements],
  );
  const visibleFlows = useMemo(
    () => flows.filter((flow) =>
      visibleIds.has(`${flow.source.runId}:${flow.source.subject.ref.id}`)
      && visibleIds.has(`${flow.target.runId}:${flow.target.subject.ref.id}`)),
    [flows, visibleIds],
  );

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
          <div>
            <p className="globe-unavailable__eyebrow">GEOGRAPHY READINESS</p>
            <h3>No explicit geography is available.</h3>
            <p>No jurisdiction or coordinate was inferred.</p>
          </div>
          <dl>
            <div><dt>Loaded objects</dt><dd>{records.active.objects.length}</dd></div>
            <div><dt>Valid anchors</dt><dd>0</dd></div>
            <div><dt>Inferred positions</dt><dd>0</dd></div>
          </dl>
          <details>
            <summary>Add an evidence-backed geography overlay</summary>
            <p>
              Import a verified <code>ewm.geo-overlay.v1</code> sidecar with EPSG:4326 coordinates,
              validity, uncertainty, and source locators. The run remains unchanged.
            </p>
            <code className="globe-unavailable__command">
              ewm ontology project --run-dir &lt;run&gt; --geo-overlay &lt;overlay.json&gt; --output &lt;projection&gt;
            </code>
          </details>
        </section>
      ) : null}
      {records.key === requestKey && !records.failed && placements.length > 0 ? (
        <>
          <GlobeLegend
            activeCount={activePlacements.length}
            comparisonCount={comparisonPlacements.length}
            flowCount={visibleFlows.length}
          />
          <GlobeControls
            kinds={kinds}
            enabledKinds={effectiveKinds}
            showFlows={showFlows}
            showUncertainty={showUncertainty}
            onToggleKind={(kind) => {
              setDisabledKinds((current) => {
                const next = new Set(current);
                if (next.has(kind)) next.delete(kind);
                else next.add(kind);
                return next;
              });
            }}
            onShowFlows={setShowFlows}
            onShowUncertainty={setShowUncertainty}
          />
          {available ? (
            <SceneErrorBoundary
              key={requestKey}
              fallback={
                <GlobeLedger
                  placements={visiblePlacements}
                  flows={showFlows ? visibleFlows : []}
                  selectedId={selectedId}
                  onSelect={onSelect}
                  renderingUnavailable
                />
              }
            >
              <Suspense fallback={<p className="lens-loading">Loading bundled globe geometry…</p>}>
                <LazyEconomicGlobe
                  placements={visiblePlacements}
                  flows={visibleFlows}
                  selectedId={selectedId}
                  onSelect={onSelect}
                  showFlows={showFlows}
                  showUncertainty={showUncertainty}
                />
              </Suspense>
            </SceneErrorBoundary>
          ) : null}
          <GlobeLedger
            placements={visiblePlacements}
            flows={showFlows ? visibleFlows : []}
            selectedId={selectedId}
            onSelect={onSelect}
            renderingUnavailable={!available}
          />
        </>
      ) : null}
    </section>
  );
}

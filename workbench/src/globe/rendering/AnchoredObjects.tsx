import { Instance, Instances } from "@react-three/drei";

import { latLonToCartesian, type TaggedGeoPlacement } from "../geometry";

interface AnchoredObjectsProps {
  readonly placements: ReadonlyArray<TaggedGeoPlacement>;
  readonly selectedId: string | null;
  readonly onSelect: (id: string) => void;
}

interface MarkerGroupProps extends AnchoredObjectsProps {
  readonly role: TaggedGeoPlacement["runRole"];
}

function MarkerGroup({ placements, role, selectedId, onSelect }: MarkerGroupProps) {
  const group = placements.filter((placement) => placement.runRole === role);
  if (group.length === 0) return null;
  return (
    <Instances limit={group.length} range={group.length}>
      {role === "active" ? (
        <sphereGeometry args={[0.075, 12, 8]} />
      ) : (
        <octahedronGeometry args={[0.095, 0]} />
      )}
      <meshStandardMaterial roughness={0.72} metalness={0} vertexColors />
      {group.map((placement) => {
        const selected = placement.subject.ref.id === selectedId;
        return (
          <Instance
            key={`${placement.runId}:${placement.subject.ref.id}`}
            position={latLonToCartesian(placement.latitude, placement.longitude, 3.06)}
            color={selected ? "#f3f3eb" : role === "active" ? "#c7f24a" : "#ff7452"}
            scale={selected ? 1.65 : 1}
            onClick={(event) => {
              event.stopPropagation();
              onSelect(placement.subject.ref.id);
            }}
          />
        );
      })}
    </Instances>
  );
}

export function AnchoredObjects(props: AnchoredObjectsProps) {
  return (
    <>
      <MarkerGroup {...props} role="active" />
      <MarkerGroup {...props} role="comparison" />
    </>
  );
}

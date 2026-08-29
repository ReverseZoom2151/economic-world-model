import type { SceneNode } from "./layout";

interface WebGLFallbackProps {
  readonly nodes: ReadonlyArray<SceneNode>;
  readonly selectedId: string | null;
  readonly onSelect: (id: string) => void;
}

export function WebGLFallback({ nodes, selectedId, onSelect }: WebGLFallbackProps) {
  return (
    <section className="webgl-fallback" aria-label="3D scene fallback">
      <header>
        <div>
          <p>Accessible 2D equivalent</p>
          <h3>3D rendering unavailable</h3>
        </div>
        <strong>No investigation data were discarded.</strong>
      </header>
      {nodes.length === 0 ? (
        <p className="evidence-absence">No scene objects are available in the selected layers.</p>
      ) : (
        <table>
          <thead>
            <tr><th>Object</th><th>Lane</th><th>Layer</th><th>Depth</th><th /></tr>
          </thead>
          <tbody>
            {nodes.map((node) => (
              <tr key={node.id} data-selected={selectedId === node.id}>
                <td><strong>{node.label}</strong></td>
                <td>{node.lane}</td>
                <td>{node.layer.replaceAll("_", " ")}</td>
                <td>{node.position[2]} · {node.depthBasis.replaceAll("_", " ")}</td>
                <td>
                  <button type="button" onClick={() => onSelect(node.id)} aria-label={`Select ${node.label}`}>
                    Select
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

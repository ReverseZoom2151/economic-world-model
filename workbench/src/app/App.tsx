export function App() {
  return (
    <main className="launch" aria-labelledby="workbench-title">
      <div className="launch__index" aria-hidden="true">
        EWM / 00
      </div>
      <section className="launch__field">
        <p className="launch__eyebrow">Local research instrument</p>
        <h1 id="workbench-title">Ontology Research Workbench</h1>
        <p className="launch__thesis">
          Follow economic behavior into markets, evidence, and the models trained next.
        </p>
      </section>
      <aside className="launch__status" aria-label="Workbench status">
        <span className="launch__signal" aria-hidden="true" />
        <span>Client foundation ready</span>
        <small>ewm.ontology.v1</small>
      </aside>
    </main>
  );
}

import { useInvestigation } from "../state/investigation";

export function Timeline() {
  const { state, dispatch } = useInvestigation();
  const start = state.timeWindow?.start ?? 0;
  const end = state.timeWindow?.end ?? 100;

  return (
    <section className="timeline" aria-label="Event timeline">
      <div className="timeline__label">
        <span>04</span>
        <strong>Event window</strong>
      </div>
      <label>
        <span>From</span>
        <input
          aria-label="Event window start"
          type="number"
          min="0"
          value={start}
          onChange={(event) =>
            dispatch({
              type: "set-time-window",
              window: { start: Number(event.currentTarget.value), end },
            })
          }
        />
      </label>
      <div className="timeline__rule" aria-hidden="true">
        <span />
      </div>
      <label>
        <span>To</span>
        <input
          aria-label="Event window end"
          type="number"
          min="0"
          value={end}
          onChange={(event) =>
            dispatch({
              type: "set-time-window",
              window: { start, end: Number(event.currentTarget.value) },
            })
          }
        />
      </label>
      <button
        type="button"
        className="text-button"
        onClick={() => dispatch({ type: "set-time-window", window: null })}
      >
        Reset
      </button>
    </section>
  );
}

import {
  type PropsWithChildren,
  useEffect,
  useMemo,
  useReducer,
} from "react";

import {
  initialInvestigationState,
  investigationReducer,
  parseInvestigationUrl,
  serializeInvestigationUrl,
} from "./model";
import { InvestigationContext } from "./store";

export function InvestigationProvider({ children }: PropsWithChildren) {
  const hydrated = useMemo(
    () =>
      typeof window === "undefined"
        ? initialInvestigationState
        : investigationReducer(initialInvestigationState, {
            type: "hydrate",
            state: parseInvestigationUrl(window.location.search),
          }),
    [],
  );
  const [state, dispatch] = useReducer(investigationReducer, hydrated);

  useEffect(() => {
    const search = serializeInvestigationUrl(state);
    window.history.replaceState(null, "", `${window.location.pathname}${search}`);
  }, [state]);

  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <InvestigationContext.Provider value={value}>{children}</InvestigationContext.Provider>;
}

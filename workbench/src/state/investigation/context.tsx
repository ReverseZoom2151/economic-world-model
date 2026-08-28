import { type PropsWithChildren, useEffect, useMemo, useReducer } from "react";

import {
  initialInvestigationState,
  investigationReducer,
  parseInvestigationUrl,
  serializeInvestigationUrl,
  type InvestigationState,
} from "./model";
import { InvestigationContext } from "./store";

interface InvestigationProviderProps extends PropsWithChildren {
  readonly initialState?: Partial<InvestigationState>;
}

export function InvestigationProvider({
  children,
  initialState,
}: InvestigationProviderProps) {
  const hydrated = useMemo(
    () => {
      const selected =
        initialState === undefined
          ? initialInvestigationState
          : investigationReducer(initialInvestigationState, {
              type: "hydrate",
              state: initialState,
            });
      return typeof window === "undefined"
        ? selected
        : investigationReducer(selected, {
            type: "hydrate",
            state: parseInvestigationUrl(window.location.search),
          });
    },
    [initialState],
  );
  const [state, dispatch] = useReducer(investigationReducer, hydrated);

  useEffect(() => {
    const search = serializeInvestigationUrl(state);
    window.history.replaceState(null, "", `${window.location.pathname}${search}`);
  }, [state]);

  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <InvestigationContext.Provider value={value}>{children}</InvestigationContext.Provider>;
}

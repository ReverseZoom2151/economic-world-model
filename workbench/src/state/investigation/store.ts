import { createContext, type Dispatch, useContext } from "react";

import type { InvestigationAction, InvestigationState } from "./model";

export interface InvestigationContextValue {
  readonly state: InvestigationState;
  readonly dispatch: Dispatch<InvestigationAction>;
}

export const InvestigationContext = createContext<InvestigationContextValue | null>(null);

export function useInvestigation(): InvestigationContextValue {
  const context = useContext(InvestigationContext);
  if (context === null) {
    throw new Error("useInvestigation must be called within InvestigationProvider");
  }
  return context;
}

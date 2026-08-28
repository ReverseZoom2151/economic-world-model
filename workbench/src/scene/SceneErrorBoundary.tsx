import { Component, type ReactNode } from "react";

interface SceneErrorBoundaryProps {
  readonly children: ReactNode;
  readonly fallback: ReactNode;
}

interface SceneErrorBoundaryState {
  readonly failed: boolean;
}

export class SceneErrorBoundary extends Component<
  SceneErrorBoundaryProps,
  SceneErrorBoundaryState
> {
  override state: SceneErrorBoundaryState = { failed: false };

  static getDerivedStateFromError(): SceneErrorBoundaryState {
    return { failed: true };
  }

  override render(): ReactNode {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

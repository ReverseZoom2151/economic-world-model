import type { ReactNode } from "react";

export interface TechnicalDetail {
  readonly label: string;
  readonly value: ReactNode;
}

interface TechnicalDetailsProps {
  readonly details: ReadonlyArray<TechnicalDetail>;
  readonly summary?: string;
  readonly className?: string;
}

export function TechnicalDetails({
  details,
  summary = "Technical details",
  className = "",
}: TechnicalDetailsProps) {
  const available = details.filter((detail) => detail.value !== null && detail.value !== undefined);
  if (available.length === 0) return null;

  return (
    <details className={`technical-details${className ? ` ${className}` : ""}`}>
      <summary>{summary}</summary>
      <dl>
        {available.map((detail) => (
          <div key={detail.label}>
            <dt>{detail.label}</dt>
            <dd><code>{detail.value}</code></dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

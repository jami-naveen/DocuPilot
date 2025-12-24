import type { ProcessStatus } from "../types/api";

interface Props {
  status: ProcessStatus | null;
}

export function ProgressMeter({ status }: Props) {
  if (!status) {
    return <p className="muted">No active processing run.</p>;
  }
  return (
    <div className="progress-meter">
      {status.steps.map((step) => {
        const percent = step.total ? Math.min(100, (step.current / step.total) * 100) : 0;
        return (
          <div key={step.step}>
            <div className="progress-row">
              <span>{step.step}</span>
              <span>
                {step.current}/{step.total || step.current || 0}
              </span>
            </div>
            <div className="progress-bar">
              <span style={{ width: `${percent}%` }} />
            </div>
          </div>
        );
      })}
      <p className="muted">State: {status.state}</p>
      {status.errors.length > 0 && (
        <p className="muted" style={{ color: "var(--danger)" }}>
          {status.errors.join("\n")}
        </p>
      )}
    </div>
  );
}

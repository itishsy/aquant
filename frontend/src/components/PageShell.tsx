import { ReactNode } from "react";

type Segment = {
  key: string;
  label: string;
  onClick?: () => void;
};

export function PageShell(props: {
  title: string;
  dateText?: string;
  onPrevDate?: () => void;
  onNextDate?: () => void;
  segments?: Segment[];
  activeSegment?: string;
  children: ReactNode;
}) {
  return (
    <section className="page-shell">
      <header className="top-hero">
        <button className="nav-chip" aria-label="previous" onClick={props.onPrevDate}>
          {"<"}
        </button>
        <div className="date-pill">{props.dateText || props.title}</div>
        <button className="nav-chip" aria-label="next" onClick={props.onNextDate}>
          {">"}
        </button>
      </header>

      {props.segments?.length ? (
        <div className="segment-row">
          {props.segments.map((segment) => (
            <button
              key={segment.key}
              className={`segment-pill ${props.activeSegment === segment.key ? "is-active" : ""}`}
              onClick={segment.onClick}
            >
              {segment.label}
            </button>
          ))}
        </div>
      ) : null}

      <div className="page-content">{props.children}</div>
    </section>
  );
}

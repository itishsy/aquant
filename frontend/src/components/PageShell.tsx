import { ReactNode } from "react";

type Segment = {
  key: string;
  label: string;
  onClick?: () => void;
};

export function PageShell(props: {
  title: string;
  dateText?: string;
  onDateClick?: () => void;
  onPrevDate?: () => void;
  onNextDate?: () => void;
  disablePrev?: boolean;
  disableNext?: boolean;
  segments?: Segment[];
  activeSegment?: string;
  hideHero?: boolean;
  children: ReactNode;
}) {
  return (
    <section className="page-shell">
      {!props.hideHero ? (
        <header className="top-hero">
          <button className="nav-chip" aria-label="previous" onClick={props.onPrevDate}
            disabled={props.disablePrev}
            style={props.disablePrev ? { opacity: 0.3, pointerEvents: "none" } : undefined}>
            {"<"}
          </button>
          <button className="date-pill" type="button" onClick={props.onDateClick}>
            {props.dateText || props.title}
          </button>
          <button className="nav-chip" aria-label="next" onClick={props.onNextDate}
            disabled={props.disableNext}
            style={props.disableNext ? { opacity: 0.3, pointerEvents: "none" } : undefined}>
            {">"}
          </button>
        </header>
      ) : null}

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

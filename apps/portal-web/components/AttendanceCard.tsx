"use client";

interface Props {
  data: Record<string, any>;
}

/** A compact read-out beside the prose reply, built only from what the tool returned. */
export function AttendanceCard({ data }: Props) {
  if (data.kind === "attendance" && data.ok) {
    return (
      <div className="card">
        <div className="card__head">
          <span className="card__name">{data.student_name}</span>
          <span className="card__meta">
            {data.roll_number} · {data.class_name}
          </span>
        </div>
        <div className="card__figure">{data.percentage}%</div>
        <div className="card__stats">
          <span><b>{data.present_days}</b> present</span>
          <span><b>{data.absent_days}</b> absent</span>
          <span><b>{data.late_days}</b> late</span>
        </div>
        <div className="card__strip">
          {(data.recent ?? []).slice().reverse().map((row: any) => (
            <span key={row.date} className={`pip pip--${row.status}`} title={`${row.date}: ${row.status}`} />
          ))}
        </div>
      </div>
    );
  }

  if (data.kind === "analytics" && data.ok) {
    const trendClass =
      data.trend_direction === "improving"
        ? "trend--improving"
        : data.trend_direction === "declining"
        ? "trend--declining"
        : "trend--stable";

    const trendSymbol =
      data.trend_direction === "improving"
        ? "↗"
        : data.trend_direction === "declining"
        ? "↘"
        : "→";

    return (
      <div className="card card--analytics">
        <div className="card__head">
          <div>
            <span className="card__name">School-wide Analytics</span>
            <span className="card__meta">Last {data.window_days} days · {data.records_considered} records</span>
          </div>
          {data.trend_direction && (
            <span className={`card__trend-badge ${trendClass}`}>
              {trendSymbol} {data.trend_direction} {data.trend_change !== undefined && `(${data.trend_change > 0 ? "+" : ""}${data.trend_change}%)`}
            </span>
          )}
        </div>

        <div className="card__kpis">
          <div className="kpi">
            <span className="kpi__label">Overall Rate</span>
            <span className="kpi__value">{data.overall_percentage}%</span>
            <span className="kpi__sub">{data.total_students} students</span>
          </div>
          <div className="kpi">
            <span className="kpi__label">Today's Check-in</span>
            <span className="kpi__value">
              {data.today?.present ?? 0}
              <small>/{data.total_students ?? 0}</small>
            </span>
            <span className="kpi__sub">
              {data.today?.in_progress
                ? `still being marked · ${data.today?.marked ?? 0} of ${data.today?.roll_size ?? 0} recorded`
                : `${data.today?.absent ?? 0} absent · ${data.today?.late ?? 0} late`}
            </span>
          </div>
          <div className="kpi">
            <span className="kpi__label">At-Risk (&lt;75%)</span>
            <span className={`kpi__value ${data.students_below_75_percent > 0 ? "kpi__value--warn" : ""}`}>
              {data.students_below_75_percent}
            </span>
            <span className="kpi__sub">
              {data.at_risk_percentage !== undefined ? `${data.at_risk_percentage}% of school` : "students"}
            </span>
          </div>
        </div>

        {data.recent_daily_trend && data.recent_daily_trend.length > 0 && (
          <div className="card__trend-section">
            <div className="card__section-title">Daily Attendance Trend (Last 7 Days)</div>
            <div className="trend-bars">
              {data.recent_daily_trend.map((day: any) => {
                // A day still being marked is shown hatched, not as a 0% collapse —
                // it is excluded from the trend maths for the same reason.
                const partial = Boolean(day.in_progress);
                const height = Math.max(15, Math.min(100, day.percentage));
                const barClass = partial
                  ? "trend-bar--partial"
                  : day.percentage >= 90
                  ? "trend-bar--ok"
                  : day.percentage >= 75
                  ? "trend-bar--warn"
                  : "trend-bar--bad";
                const tip = partial
                  ? `${day.date} (${day.day_name}): still being marked — ${day.marked} of ${day.roll_size} recorded`
                  : `${day.date} (${day.day_name}): ${day.percentage}% (${day.present} present, ${day.absent} absent)`;
                return (
                  <div key={day.date} className={`trend-col${partial ? " trend-col--partial" : ""}`} title={tip}>
                    <span className="trend-col__pct">{partial ? "—" : `${day.percentage}%`}</span>
                    <div className="trend-col__track">
                      <div
                        className={`trend-col__fill ${barClass}`}
                        style={{ height: partial ? "100%" : `${height}%` }}
                      />
                    </div>
                    <span className="trend-col__label">{day.day_name}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {data.weekday_breakdown && data.weekday_breakdown.length > 1 && (
          <div className="card__trend-section">
            <div className="card__section-title">Attendance by Weekday</div>
            <div className="weekday-row">
              {data.weekday_breakdown.map((day: any) => {
                const tone =
                  day.percentage >= 90 ? "ok" : day.percentage >= 75 ? "warn" : "bad";
                return (
                  <div
                    key={day.day}
                    className={`weekday weekday--${tone}`}
                    title={`${day.day}: ${day.percentage}% across ${day.records} records`}
                  >
                    <span className="weekday__day">{day.short_day}</span>
                    <span className="weekday__pct">{day.percentage}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="card__section-title">Class Breakdown</div>
        <div className="card__bars">
          {(data.by_class ?? []).map((row: any) => {
            const fillClass =
              row.percentage >= 90
                ? "bar__fill--ok"
                : row.percentage >= 75
                ? "bar__fill--warn"
                : "bar__fill--bad";
            return (
              <div key={row.class_name} className="bar">
                <span className="bar__label">{row.class_name}</span>
                <span className="bar__track">
                  <span
                    className={`bar__fill ${fillClass}`}
                    style={{ width: `${Math.min(100, Math.max(5, row.percentage))}%` }}
                  />
                </span>
                <span className="bar__value">{row.percentage}%</span>
              </div>
            );
          })}
        </div>

        {(data.highest_class || data.lowest_class) && (
          <div className="card__insights">
            {data.highest_class && (
              <span className="insight-pill insight-pill--ok">
                🏆 Top: <strong>{data.highest_class}</strong>
              </span>
            )}
            {data.lowest_class && (
              <span className="insight-pill insight-pill--warn">
                ⚠️ Lowest: <strong>{data.lowest_class}</strong>
              </span>
            )}
          </div>
        )}
      </div>
    );
  }

  if (data.kind === "mark_attendance" && data.ok) {
    return (
      <div className="card card--confirm">
        <div className="card__head">
          <span className="card__name">Recorded</span>
          <span className="card__meta">{data.date}</span>
        </div>
        <p className="card__line">
          {data.student_name} → <b className={`status status--${data.status}`}>{data.status}</b>
          {data.previous_status && data.previous_status !== data.status ? ` (was ${data.previous_status})` : ""}
        </p>
      </div>
    );
  }

  if (data.kind === "escalation_result" && data.ok) {
    return (
      <div className="card card--confirm">
        <div className="card__head">
          <span className="card__name">Call request sent</span>
          <span className="card__meta">{data.ticket_ref}</span>
        </div>
        <p className="card__line">Queued for {data.target_name}.</p>
      </div>
    );
  }

  return null;
}

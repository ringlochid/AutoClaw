import { IdRefText, StatePanel, StatusChip, Surface, TimestampText } from "../../components/ui";
import { classNames } from "../../lib/classNames";
import type { TaskEventRow } from "./task-detail-model";

export function TaskEventLane({
    events,
    onOpenDetail,
    onSelectEvent,
    selectedEventId,
}: {
    readonly events: readonly TaskEventRow[];
    readonly onOpenDetail: () => void;
    readonly onSelectEvent: (eventId: string) => void;
    readonly selectedEventId: string | null;
}) {
    return (
        <Surface className="min-w-0" label="Events" title="Task event chronology">
            {events.length === 0 ? (
                <StatePanel
                    summary="No persisted task-event history was returned for the current snapshot anchor."
                    title="No event history"
                    tone="empty"
                />
            ) : (
                <ol
                    aria-label="Task events"
                    className="max-h-[38rem] space-y-2 overflow-y-auto pr-1"
                >
                    {events.map((event) => (
                        <li key={event.eventId}>
                            <button
                                aria-pressed={event.eventId === selectedEventId}
                                className={classNames(
                                    "w-full rounded-card border p-3 text-left shadow-hairline transition-colors hover:border-primary/35 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                                    event.eventId === selectedEventId
                                        ? "border-primary/40 bg-primary-soft"
                                        : "border-outline-soft bg-surface-low",
                                )}
                                onClick={() => {
                                    onSelectEvent(event.eventId);
                                }}
                                onDoubleClick={onOpenDetail}
                                type="button"
                            >
                                <div className="grid min-w-0 gap-2">
                                    <div className="min-w-0">
                                        <div className="flex min-w-0 flex-wrap items-center gap-2">
                                            <StatusChip
                                                className="max-w-full min-w-0 break-all"
                                                tone={event.tone}
                                                withDot
                                            >
                                                {event.eventType}
                                            </StatusChip>
                                            {event.nodeKey === null ? null : (
                                                <IdRefText
                                                    className="max-w-40 truncate"
                                                    value={event.nodeKey}
                                                />
                                            )}
                                        </div>
                                        <p className="mt-2 line-clamp-2 text-compact text-foreground">
                                            {event.payloadSummary}
                                        </p>
                                    </div>
                                    <TimestampText
                                        className="text-muted"
                                        value={event.occurredAt}
                                    />
                                </div>
                            </button>
                        </li>
                    ))}
                </ol>
            )}
        </Surface>
    );
}

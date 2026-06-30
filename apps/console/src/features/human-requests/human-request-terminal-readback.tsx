import {
    CodeBlock,
    IdRefText,
    PropertyGrid,
    StatusChip,
    Surface,
    TimestampText,
} from "../../components/ui";
import type { components } from "../../api/generated/openapi";

type HumanRequestItemResponse = components["schemas"]["HumanRequestItemResponse"];
type HumanRequestRead = components["schemas"]["HumanRequestRead"];
type HumanRequestResolution = components["schemas"]["HumanRequestResolution"];
type HumanRequestStatus = components["schemas"]["HumanRequestStatus"];

export function TerminalReadback({ read }: { readonly read: HumanRequestRead }) {
    const resolution = read.resolution ?? null;

    return (
        <Surface label="Terminal readback" title={terminalTitle(read.request.status, resolution)}>
            {resolution === null ? (
                <p className="text-compact text-muted">
                    The request is terminal, but the list response did not include resolution
                    detail.
                </p>
            ) : (
                <div className="space-y-4">
                    <PropertyGrid
                        items={[
                            {
                                label: "Resolution kind",
                                value: resolution.resolution_kind,
                            },
                            {
                                label: "Resolved",
                                value: <TimestampText value={resolution.resolved_at} />,
                            },
                            {
                                label: "Resolved by",
                                value: resolution.resolved_by_actor_ref ?? "Unknown actor",
                            },
                        ]}
                    />
                    {resolution.item_responses.length === 0 ? (
                        <p className="text-compact text-muted">
                            No item responses were persisted for this terminal outcome.
                        </p>
                    ) : (
                        <ol className="space-y-2">
                            {resolution.item_responses.map((response) => (
                                <li
                                    className="rounded-card border border-outline-soft bg-surface-low p-3"
                                    key={response.item_id}
                                >
                                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                                        <IdRefText value={response.item_id} />
                                        {response.selected_option === null ||
                                        response.selected_option === undefined ? null : (
                                            <StatusChip tone="success">
                                                {response.selected_option}
                                            </StatusChip>
                                        )}
                                    </div>
                                    {response.freeform_answer === null ||
                                    response.freeform_answer === undefined ? null : (
                                        <p className="mt-2 text-compact text-foreground">
                                            {response.freeform_answer}
                                        </p>
                                    )}
                                    {response.extra_notes === null ||
                                    response.extra_notes === undefined ? null : (
                                        <p className="mt-2 text-compact text-muted">
                                            {response.extra_notes}
                                        </p>
                                    )}
                                    {hasResponsePayload(response) ? (
                                        <CodeBlock className="mt-3" title="Response payload">
                                            {formatResponsePayload(response.response_payload)}
                                        </CodeBlock>
                                    ) : null}
                                </li>
                            ))}
                        </ol>
                    )}
                </div>
            )}
        </Surface>
    );
}

function terminalTitle(
    status: HumanRequestStatus,
    resolution: HumanRequestResolution | null,
): string {
    if (resolution?.resolution_kind === "answered" || status === "resolved") {
        return "Resolved request";
    }
    if (resolution?.resolution_kind === "timed_out" || status === "timed_out") {
        return "Timed out request";
    }
    if (resolution?.resolution_kind === "cancelled" || status === "cancelled") {
        return "Cancelled request";
    }
    return "Terminal request";
}

function hasResponsePayload(
    response: HumanRequestItemResponse,
): response is HumanRequestItemResponse & {
    readonly response_payload: NonNullable<HumanRequestItemResponse["response_payload"]>;
} {
    return response.response_payload !== null && response.response_payload !== undefined;
}

function formatResponsePayload(
    payload: NonNullable<HumanRequestItemResponse["response_payload"]>,
): string {
    return JSON.stringify(payload, null, 2);
}

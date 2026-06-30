import type { ReactNode } from "react";

import type { components } from "../../api/generated/openapi";
import type { CommandRunRow } from "../../api/view-models";
import type { StatusTone } from "../../components/ui";

export type CommandRunState = components["schemas"]["CommandRunState"];
export type CommandRunRecord = components["schemas"]["CommandRunRecord"];
export type CommandRunLogReadResponse = components["schemas"]["CommandRunLogReadResponse"];

export interface CommandRunDetailView {
    readonly attemptId: string | null;
    readonly cancellationRequestedAt: string | null;
    readonly cancellationRequestedByActorRef: string | null;
    readonly command: string;
    readonly createdAt: string;
    readonly description: string;
    readonly dispatchId: string;
    readonly endedAt: string | null;
    readonly latestLogRef: string | null;
    readonly latestUpdate: string | null;
    readonly logRef: string | null;
    readonly runId: string;
    readonly startedAt: string | null;
    readonly state: CommandRunState;
    readonly stateLabel: string;
    readonly stateTone: StatusTone;
    readonly taskId: string;
    readonly terminalActorRef: string | null;
    readonly terminalEventSource: components["schemas"]["TaskEventSource"] | null;
    readonly terminalResult: components["schemas"]["CommandRunTerminalResult"] | null;
    readonly timeoutSeconds: number | null;
    readonly workdir: string | null;
}

export interface CommandRunRowView extends CommandRunRow {
    readonly canCancel: boolean;
    readonly stateLabel: string;
    readonly stateTone: StatusTone;
}

export function mapCommandRunRowView(row: CommandRunRow): CommandRunRowView {
    return {
        ...row,
        canCancel: isCommandRunCancellable(row.state),
        stateLabel: commandRunStateLabel(row.state),
        stateTone: commandRunStateTone(row.state),
    };
}

export function mapCommandRunDetailView(record: CommandRunRecord): CommandRunDetailView {
    const terminalLogRef = record.terminal_result?.log_ref ?? null;
    const latestLogRef = record.latest_log_ref ?? null;

    return {
        attemptId: record.attempt_id ?? null,
        cancellationRequestedAt: record.cancellation_requested_at ?? null,
        cancellationRequestedByActorRef: record.cancellation_requested_by_actor_ref ?? null,
        command: record.command,
        createdAt: record.created_at,
        description: record.description,
        dispatchId: record.dispatch_id,
        endedAt: record.ended_at ?? null,
        latestLogRef,
        latestUpdate: record.latest_update ?? null,
        logRef: terminalLogRef ?? latestLogRef,
        runId: record.run_id,
        startedAt: record.started_at ?? null,
        state: record.state,
        stateLabel: commandRunStateLabel(record.state),
        stateTone: commandRunStateTone(record.state),
        taskId: record.task_id,
        terminalActorRef: record.terminal_actor_ref ?? null,
        terminalEventSource: record.terminal_event_source ?? null,
        terminalResult: record.terminal_result ?? null,
        timeoutSeconds: record.timeout_seconds ?? null,
        workdir: record.workdir ?? null,
    };
}

export function isCommandRunCancellable(state: CommandRunState): boolean {
    return state === "pending_start" || state === "running";
}

export function isTerminalCommandRunState(state: CommandRunState): boolean {
    return (
        state === "succeeded" ||
        state === "failed" ||
        state === "timed_out" ||
        state === "cancelled"
    );
}

export function commandRunStateLabel(state: CommandRunState): string {
    switch (state) {
        case "pending_start":
            return "Queued";
        case "running":
            return "Running";
        case "cancellation_requested":
            return "Cancel requested";
        case "succeeded":
            return "Succeeded";
        case "failed":
            return "Failed";
        case "timed_out":
            return "Timed out";
        case "cancelled":
            return "Cancelled";
    }
}

export function commandRunStateTone(state: CommandRunState): StatusTone {
    switch (state) {
        case "running":
            return "active";
        case "succeeded":
            return "success";
        case "failed":
        case "timed_out":
        case "cancelled":
            return "danger";
        case "pending_start":
        case "cancellation_requested":
            return "warning";
    }
}

export function formatOptionalNumber(value: number | null): string {
    return value === null ? "Not reported" : String(value);
}

export function renderOptionalText(value: string | null): ReactNode {
    return value === null || value.trim() === "" ? "Not reported" : value;
}

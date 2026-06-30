import type { StatusTone } from "../../components/ui";
import type { components } from "../../api/generated/openapi";

export function flowStatusTone(status: components["schemas"]["FlowStatus"]): StatusTone {
    switch (status) {
        case "running":
            return "active";
        case "succeeded":
            return "success";
        case "blocked":
        case "cancelled":
            return "danger";
        case "paused":
        case "pending":
            return "warning";
    }
}

export function commandRunTone(status: components["schemas"]["CommandRunState"]): StatusTone {
    switch (status) {
        case "running":
        case "cancellation_requested":
            return "active";
        case "succeeded":
            return "success";
        case "failed":
        case "timed_out":
        case "cancelled":
            return "danger";
        case "pending_start":
            return "warning";
    }
}

export function humanRequestTone(status: components["schemas"]["HumanRequestStatus"]): StatusTone {
    switch (status) {
        case "open":
            return "warning";
        case "resolved":
            return "success";
        case "cancelled":
        case "timed_out":
            return "danger";
    }
}

export function taskEventTone(eventType: components["schemas"]["TaskEventType"]): StatusTone {
    if (eventType.startsWith("command_run_failed") || eventType.endsWith("cancelled")) {
        return "danger";
    }
    if (eventType.includes("succeeded") || eventType === "boundary_accepted") {
        return "success";
    }
    if (eventType.includes("human_request") || eventType.includes("checkpoint")) {
        return "warning";
    }
    return "active";
}

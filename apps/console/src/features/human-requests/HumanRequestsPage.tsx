import { useParams } from "react-router-dom";

import { RouteScaffold } from "../../components/layout";

export function HumanRequestsPage() {
    const { taskId } = useParams();

    return (
        <RouteScaffold
            backingSurfaces={[
                "GET /control/tasks/{task_id}/human-requests",
                "POST /control/tasks/{task_id}/human-requests/{request_id}/resolve",
            ]}
            eyebrow={taskId ?? "Runtime"}
            title="Human Requests"
        />
    );
}

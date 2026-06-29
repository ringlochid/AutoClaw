import { useParams } from "react-router-dom";

import { RouteScaffold } from "../../components/layout";

export function TaskDetailPage() {
    const { taskId } = useParams();

    return (
        <RouteScaffold
            backingSurfaces={[
                "GET /control/tasks/{task_id}",
                "GET /control/tasks/{task_id}/snapshot",
                "GET /control/tasks/{task_id}/trace",
                "GET /control/tasks/{task_id}/events",
                "GET /control/tasks/{task_id}/events/stream",
            ]}
            eyebrow={taskId ?? "Runtime"}
            title="Task Detail"
        />
    );
}

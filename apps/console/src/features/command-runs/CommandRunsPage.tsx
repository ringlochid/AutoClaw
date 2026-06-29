import { useParams } from "react-router-dom";

import { RouteScaffold } from "../../components/layout";

export function CommandRunsPage() {
    const { taskId } = useParams();

    return (
        <RouteScaffold
            backingSurfaces={[
                "GET /control/tasks/{task_id}/command-runs",
                "GET /control/tasks/{task_id}/command-runs/{run_id}",
                "GET /control/tasks/{task_id}/command-runs/{run_id}/log",
                "POST /control/tasks/{task_id}/command-runs/{run_id}/cancel",
            ]}
            eyebrow={taskId ?? "Runtime"}
            title="Command Runs"
        />
    );
}

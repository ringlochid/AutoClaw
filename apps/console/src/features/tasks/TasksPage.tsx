import { RouteScaffold } from "../../components/layout";

export function TasksPage() {
    return (
        <RouteScaffold backingSurfaces={["GET /runtime/tasks"]} eyebrow="Runtime" title="Tasks" />
    );
}

import { RouteScaffold } from "../../components/layout";

export function TaskStartPage() {
    return (
        <RouteScaffold
            backingSurfaces={[
                "GET /definitions/workflows",
                "GET /definitions/{kind}/{key}",
                "POST /tasks/start",
            ]}
            eyebrow="Authoring"
            title="Task Start"
        />
    );
}

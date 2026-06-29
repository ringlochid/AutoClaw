import { RouteScaffold } from "../../components/layout";

export function DefinitionsPage() {
    return (
        <RouteScaffold
            backingSurfaces={[
                "GET /definitions/roles",
                "GET /definitions/policies",
                "GET /definitions/workflows",
                "GET /definitions/{kind}/{key}",
                "GET /definitions/{kind}/{key}/versions",
            ]}
            eyebrow="Authoring"
            title="Definitions"
        />
    );
}

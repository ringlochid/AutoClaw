import { RouteScaffold } from "../../components/layout";

export function DefinitionEditorPage() {
    return (
        <RouteScaffold
            backingSurfaces={[
                "GET /authoring/definition-draft-sets",
                "POST /authoring/definition-draft-sets",
                "GET /authoring/definition-draft-sets/{draft_set_id}",
                "PUT /authoring/definition-draft-sets/{draft_set_id}/files/{kind}/{key}",
                "POST /authoring/definition-draft-sets/{draft_set_id}/validate",
                "POST /authoring/definition-draft-sets/{draft_set_id}/apply",
            ]}
            eyebrow="Authoring"
            title="Definition Editor"
        />
    );
}

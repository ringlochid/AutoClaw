import { RefreshCw } from "lucide-react";

import { PageFrame } from "../../components/layout";
import { Button } from "../../components/ui";
import {
    PreviewPanel,
    ResultPanel,
    RootsSection,
    TaskIdentitySection,
    TaskStartActions,
} from "./task-start-form-sections";
import { WorkflowSection } from "./task-start-workflow-section";
import { useTaskStartController } from "./task-start-controller";

export function TaskStartPage() {
    const controller = useTaskStartController();

    return (
        <PageFrame
            actions={
                <Button
                    disabled={controller.listState.isLoading || controller.listState.isRefreshing}
                    icon={
                        <RefreshCw
                            className={controller.listState.isRefreshing ? "animate-spin" : ""}
                        />
                    }
                    onClick={controller.refresh}
                >
                    Refresh
                </Button>
            }
            description="Launch a new task from current stored workflow truth with bounded task inputs."
            eyebrow="Authoring"
            title="Task Start"
        >
            <div className="space-y-4">
                <WorkflowSection controller={controller} />
                <TaskIdentitySection controller={controller} />
                <RootsSection controller={controller} />
                <TaskStartActions controller={controller} />
                {controller.previewOpen && controller.preview !== null ? (
                    <PreviewPanel
                        onClose={() => {
                            controller.setPreviewOpen(false);
                        }}
                        preview={controller.preview}
                    />
                ) : null}
                <ResultPanel controller={controller} />
            </div>
        </PageFrame>
    );
}

import { PageFrame } from "../../components/layout";
import {
    PreviewPanel,
    ResultPanel,
    RootsSection,
    TaskStartSection,
    TaskIdentitySection,
    TaskStartActions,
} from "./task-start-form-sections";
import { WorkflowSection } from "./task-start-workflow-section";
import { useTaskStartController } from "./task-start-controller";

export function TaskStartPage() {
    const controller = useTaskStartController();

    return (
        <PageFrame
            className="!max-w-[1320px]"
            contentClassName="!px-0 !py-0"
            eyebrow="Authoring"
            title="Task Start"
        >
            <div className="space-y-4">
                <div className="divide-y divide-outline-soft">
                    <TaskStartSection label="Workflow">
                        <WorkflowSection controller={controller} />
                    </TaskStartSection>
                    <TaskStartSection label="Task">
                        <TaskIdentitySection controller={controller} />
                    </TaskStartSection>
                    <TaskStartSection label="Roots">
                        <RootsSection controller={controller} />
                    </TaskStartSection>
                    <TaskStartSection label="Launch">
                        <TaskStartActions controller={controller} />
                    </TaskStartSection>
                </div>
                {controller.previewOpen && controller.preview !== null ? (
                    <PreviewPanel
                        onClose={() => {
                            controller.setPreviewOpen(false);
                        }}
                        onStart={controller.start}
                        preview={controller.preview}
                        startDisabled={controller.submitState.isSubmitting}
                    />
                ) : null}
                <ResultPanel controller={controller} />
            </div>
        </PageFrame>
    );
}

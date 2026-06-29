import { Navigate, createBrowserRouter } from "react-router-dom";

import { App } from "./App";
import { FixtureGalleryPage } from "./FixtureGalleryPage";
import { CommandRunsPage } from "../features/command-runs/CommandRunsPage";
import { DefinitionEditorPage } from "../features/definition-editor/DefinitionEditorPage";
import { DefinitionsPage } from "../features/definitions/DefinitionsPage";
import { HumanRequestsPage } from "../features/human-requests/HumanRequestsPage";
import { TaskDetailPage } from "../features/task-detail/TaskDetailPage";
import { TaskStartPage } from "../features/task-start/TaskStartPage";
import { TasksPage } from "../features/tasks/TasksPage";

export const router = createBrowserRouter([
    {
        element: <App />,
        path: "/",
        children: [
            {
                element: <Navigate replace to="/tasks" />,
                index: true,
            },
            {
                element: <TasksPage />,
                path: "tasks",
            },
            {
                element: <HumanRequestsPage />,
                path: "tasks/:taskId/human-requests",
            },
            {
                element: <CommandRunsPage />,
                path: "tasks/:taskId/command-runs",
            },
            {
                element: <TaskDetailPage />,
                path: "tasks/:taskId",
            },
            {
                element: <DefinitionsPage />,
                path: "definitions",
            },
            {
                element: <DefinitionEditorPage />,
                path: "definitions/editor",
            },
            {
                element: <TaskStartPage />,
                path: "task-start",
            },
            {
                element: <FixtureGalleryPage />,
                path: "fixtures",
            },
            {
                element: <Navigate replace to="/tasks" />,
                path: "*",
            },
        ],
    },
]);

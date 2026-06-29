import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";

import { router } from "./app/router";
import "./styles/tailwind.css";

const rootElement = document.getElementById("root");

if (rootElement === null) {
    throw new Error("AutoClaw console root element was not found");
}

createRoot(rootElement).render(
    <StrictMode>
        <RouterProvider router={router} />
    </StrictMode>,
);

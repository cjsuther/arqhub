import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider, createBrowserRouter, Navigate } from "react-router-dom";

import "./index.css";
import { AppLayout } from "./app/AppLayout";
import { EditorPage } from "./canvas/EditorPage";
import { AnalysisPage } from "./features/analysis/AnalysisPage";
import { ApprovalsPage } from "./features/approvals/ApprovalsPage";
import { CatalogPage } from "./features/catalog/CatalogPage";
import { ElementDetailPage } from "./features/catalog/ElementDetailPage";
import { UsersPage } from "./features/users/UsersPage";
import { ViewsPage } from "./features/views/ViewsPage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 10_000, refetchOnWindowFocus: false } },
});

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/catalog" replace /> },
      { path: "catalog", element: <CatalogPage /> },
      { path: "catalog/:slug", element: <ElementDetailPage /> },
      { path: "views", element: <ViewsPage /> },
      { path: "approvals", element: <ApprovalsPage /> },
      { path: "analysis", element: <AnalysisPage /> },
      { path: "users", element: <UsersPage /> },
    ],
  },
  // Editor is full-screen (its own chrome), outside the app shell.
  { path: "/views/:slug/edit", element: <EditorPage /> },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>,
);

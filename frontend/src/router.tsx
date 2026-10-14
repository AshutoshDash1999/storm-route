import { createBrowserRouter } from "react-router";

import { RouteError } from "@/src/app/RouteError";
import { RouteAnalysisPage } from "@/src/pages/RouteAnalysisPage";
import { RouteDetailsPage } from "@/src/pages/RouteDetailsPage";
import { TripPlannerPage } from "@/src/pages/TripPlannerPage";

export const router = createBrowserRouter([
  {
    errorElement: <RouteError />,
    children: [
      { path: "/", element: <TripPlannerPage /> },
      { path: "/routes", element: <RouteAnalysisPage /> },
      { path: "/routes/:routeId", element: <RouteDetailsPage /> },
    ],
  },
]);

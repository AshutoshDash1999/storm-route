import { isRouteErrorResponse, Link, useRouteError } from "react-router";
import { TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";

export function RouteError() {
  const error = useRouteError();
  const notFound = isRouteErrorResponse(error) && error.status === 404;
  return (
    <Empty className="min-h-svh">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <TriangleAlert />
        </EmptyMedia>
        <EmptyTitle>{notFound ? "Page not found" : "Something went wrong"}</EmptyTitle>
        <EmptyDescription>
          {notFound
            ? "That page doesn't exist."
            : error instanceof Error
              ? error.message
              : "An unexpected error occurred."}
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button nativeButton={false} render={<Link to="/" />}>Back to Trip Planner</Button>
      </EmptyContent>
    </Empty>
  );
}

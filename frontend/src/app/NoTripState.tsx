import type { ReactNode } from "react";
import { Route as RouteIcon } from "lucide-react";
import { Link } from "react-router";

import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { AppHeader } from "@/src/app/AppHeader";

export function NoTripState({
  title = "No trip analyzed yet",
  description = "Enter trip details or load the demo scenario to compare routes.",
  action,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex min-h-svh flex-col">
      <AppHeader mode={null} />
      <Empty className="flex-1">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <RouteIcon />
          </EmptyMedia>
          <EmptyTitle>{title}</EmptyTitle>
          <EmptyDescription>{description}</EmptyDescription>
        </EmptyHeader>
        <EmptyContent>{action ?? <Button nativeButton={false} render={<Link to="/" />}>Plan a trip</Button>}</EmptyContent>
      </Empty>
    </div>
  );
}

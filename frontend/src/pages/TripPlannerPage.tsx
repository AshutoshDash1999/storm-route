import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AppHeader } from "@/src/app/AppHeader";
import { useTrip } from "@/src/app/trip-context";
import { TripForm } from "@/src/features/trip/TripForm";

export function TripPlannerPage() {
  const { analysis } = useTrip();

  return (
    <div className="flex min-h-svh flex-col bg-muted/40">
      <AppHeader mode={analysis?.mode ?? null} />
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-6 px-4 py-10">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight">Plan a weather-aware trip</h1>
          <p className="text-muted-foreground">
            Compare up to three routes, checkpoint by checkpoint, against the forecast for
            your departure window.
          </p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Trip details</CardTitle>
            <CardDescription>All fields are required.</CardDescription>
          </CardHeader>
          <CardContent>
            <TripForm />
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

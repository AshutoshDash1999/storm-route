import { useId } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ArrowRightLeft, CircleAlert, FlaskConical, Route as RouteIcon } from "lucide-react";
import { Controller, useForm } from "react-hook-form";
import { useNavigate } from "react-router";
import { toast } from "sonner";

import { Alert, AlertAction, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
  InputGroupText,
} from "@/components/ui/input-group";
import { Spinner } from "@/components/ui/spinner";
import { useTrip } from "@/src/app/trip-context";
import { DateTimePicker } from "@/src/features/trip/DateTimePicker";
import { LocationCombobox } from "@/src/features/trip/LocationCombobox";
import {
  toFormValues,
  toTripInput,
  tripFormSchema,
  type TripFormInput,
  type TripFormOutput,
} from "@/src/features/trip/trip-schema";
import { api, ApiError } from "@/src/lib/api";
import { CHECKPOINT_INTERVAL_MI, FORECAST_HOURS } from "@/src/lib/constants";
import type { RouteAnalysis, TripInput } from "@/src/lib/types";

/** Backend request field → form field that shows its error */
const FIELD_FOR = {
  origin: "origin",
  destination: "destination",
  departureAt: "departureTime",
  loadWeightLb: "loadWeightLb",
} as const satisfies Record<string, keyof TripFormInput>;

function fieldErrors(error: unknown) {
  if (!(error instanceof ApiError)) return [];
  return Object.entries(error.fields).flatMap(([key, messages]) =>
    key in FIELD_FOR ? [[FIELD_FOR[key as keyof typeof FIELD_FOR], messages[0]] as const] : [],
  );
}

export function TripForm() {
  const ids = useId();
  const navigate = useNavigate();
  const { draft, setDraft, setAnalysis } = useTrip();

  const form = useForm<TripFormInput, unknown, TripFormOutput>({
    resolver: zodResolver(tripFormSchema),
    defaultValues: toFormValues(draft),
    mode: "onTouched",
  });
  const { errors, isSubmitted } = form.formState;
  const errorCount = Object.keys(errors).length;

  const onSuccess = (analysis: RouteAnalysis) => {
    setAnalysis(analysis);
    navigate("/routes");
  };

  const analyze = useMutation({
    mutationFn: (trip: TripInput) => api.analyzeRoutes(trip),
    onSuccess,
    onError: (error) => {
      fieldErrors(error).forEach(([field, message], i) =>
        form.setError(field, { message }, { shouldFocus: i === 0 }),
      );
    },
  });

  const demo = useMutation({
    mutationFn: () => api.loadDemo(),
    onSuccess: (analysis) => {
      form.reset(toFormValues(analysis.trip));
      toast.info("Demo scenario loaded", { description: "Showing simulated routes and weather." });
      onSuccess(analysis);
    },
    onError: () => toast.error("Couldn't load the demo scenario. Try again."),
  });

  const busy = analyze.isPending || demo.isPending;
  const apiError = analyze.error && fieldErrors(analyze.error).length === 0 ? analyze.error : null;

  const submit = form.handleSubmit((values) => {
    const trip = toTripInput(values);
    setDraft(trip);
    analyze.mutate(trip);
  });

  const swap = () => {
    const { origin, destination } = form.getValues();
    form.setValue("origin", destination, { shouldValidate: isSubmitted });
    form.setValue("destination", origin, { shouldValidate: isSubmitted });
  };

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-6">
      {isSubmitted && errorCount > 0 && (
        <Alert variant="destructive">
          <CircleAlert />
          <AlertTitle>
            Fix {errorCount} field{errorCount === 1 ? "" : "s"} to analyze routes
          </AlertTitle>
          <AlertDescription>Each problem is described below its field.</AlertDescription>
        </Alert>
      )}
      {apiError && (
        <Alert variant="destructive">
          <CircleAlert />
          <AlertTitle>Route analysis failed</AlertTitle>
          <AlertDescription>{apiError.message}</AlertDescription>
          <AlertAction>
            <Button size="sm" variant="outline" type="submit">
              Retry
            </Button>
          </AlertAction>
        </Alert>
      )}

      <FieldGroup>
        <div className="grid items-start gap-4 md:grid-cols-[1fr_auto_1fr]">
          <Controller
            control={form.control}
            name="origin"
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid || undefined}>
                <FieldLabel htmlFor={`${ids}-origin`}>Origin</FieldLabel>
                <LocationCombobox
                  id={`${ids}-origin`}
                  value={field.value}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                  placeholder="Search a US city"
                  invalid={fieldState.invalid}
                  disabled={busy}
                />
                <FieldError errors={[fieldState.error]} />
              </Field>
            )}
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={swap}
            disabled={busy}
            aria-label="Swap origin and destination"
            className="justify-self-center md:mt-7"
          >
            <ArrowRightLeft />
          </Button>
          <Controller
            control={form.control}
            name="destination"
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid || undefined}>
                <FieldLabel htmlFor={`${ids}-destination`}>Destination</FieldLabel>
                <LocationCombobox
                  id={`${ids}-destination`}
                  value={field.value}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                  placeholder="Search a US city"
                  invalid={fieldState.invalid}
                  disabled={busy}
                />
                <FieldError errors={[fieldState.error]} />
              </Field>
            )}
          />
        </div>

        <div className="grid items-start gap-4 md:grid-cols-2">
          <Field
            data-invalid={
              !!(errors.departureDate || errors.departureTime) || undefined
            }
          >
            <FieldLabel htmlFor={`${ids}-date`}>Departure</FieldLabel>
            <Controller
              control={form.control}
              name="departureDate"
              render={({ field: dateField }) => (
                <Controller
                  control={form.control}
                  name="departureTime"
                  render={({ field: timeField }) => (
                    <DateTimePicker
                      dateId={`${ids}-date`}
                      timeId={`${ids}-time`}
                      date={dateField.value}
                      time={timeField.value}
                      onDateChange={(d) => {
                        dateField.onChange(d);
                        if (isSubmitted) form.trigger(["departureDate", "departureTime"]);
                      }}
                      onTimeChange={(t) => {
                        timeField.onChange(t);
                        if (isSubmitted) form.trigger(["departureDate", "departureTime"]);
                      }}
                      dateInvalid={!!errors.departureDate}
                      timeInvalid={!!errors.departureTime}
                    />
                  )}
                />
              )}
            />
            <FieldDescription>Local time at the origin.</FieldDescription>
            <FieldError errors={[errors.departureDate, errors.departureTime]} />
          </Field>

          <Controller
            control={form.control}
            name="loadWeightLb"
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid || undefined}>
                <FieldLabel htmlFor={`${ids}-weight`}>Load weight</FieldLabel>
                <InputGroup>
                  <InputGroupInput
                    id={`${ids}-weight`}
                    type="number"
                    inputMode="numeric"
                    min={1}
                    step={500}
                    placeholder="e.g. 42000"
                    aria-invalid={fieldState.invalid || undefined}
                    disabled={busy}
                    name={field.name}
                    ref={field.ref}
                    value={String(field.value ?? "")}
                    onChange={(e) => field.onChange(e.target.value)}
                    onBlur={field.onBlur}
                  />
                  <InputGroupAddon align="inline-end">
                    <InputGroupText>lb</InputGroupText>
                  </InputGroupAddon>
                </InputGroup>
                <FieldDescription>
                  Loads over 30,000 lb and 40,000 lb get stricter high-wind limits.
                </FieldDescription>
                <FieldError errors={[fieldState.error]} />
              </Field>
            )}
          />
        </div>

        <dl className="grid grid-cols-2 gap-3 rounded-2xl border border-dashed p-4 text-sm">
          <div>
            <dt className="text-muted-foreground">Checkpoint interval</dt>
            <dd className="font-medium">Every {CHECKPOINT_INTERVAL_MI} miles</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Forecast range</dt>
            <dd className="font-medium">0–{FORECAST_HOURS} h after departure</dd>
          </div>
        </dl>
      </FieldGroup>

      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button
          type="button"
          variant="outline"
          size="lg"
          onClick={() => demo.mutate()}
          disabled={busy}
        >
          {demo.isPending ? <Spinner /> : <FlaskConical />}
          Load Demo Scenario
        </Button>
        <Button type="submit" size="lg" disabled={busy}>
          {analyze.isPending ? <Spinner /> : <RouteIcon />}
          {analyze.isPending ? "Analyzing routes…" : "Analyze Routes"}
        </Button>
      </div>
    </form>
  );
}

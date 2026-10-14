import { Hash, MapPin } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
} from "@/components/ui/combobox";
import { Spinner } from "@/components/ui/spinner";
import { api, ApiError } from "@/src/lib/api";
import type { Location, LocationResult } from "@/src/lib/types";
import { useDebouncedValue } from "@/src/lib/use-debounced-value";

const DEBOUNCE_MS = 300;
const MIN_QUERY_LENGTH = 2;

type SearchResponse = { query: string; results: LocationResult[]; error?: string };

export function LocationCombobox({
  id,
  value,
  onChange,
  onBlur,
  placeholder,
  invalid,
  disabled,
}: {
  id: string;
  value: Location | null;
  onChange: (value: Location | null) => void;
  onBlur?: () => void;
  placeholder: string;
  invalid?: boolean;
  disabled?: boolean;
}) {
  const [inputValue, setInputValue] = useState(value?.label ?? "");
  const [response, setResponse] = useState<SearchResponse | null>(null);

  // Follow value changes made outside the input (swap, demo trip, form reset)
  const selectedLabel = value?.label ?? "";
  const [syncedLabel, setSyncedLabel] = useState(selectedLabel);
  if (selectedLabel !== syncedLabel) {
    setSyncedLabel(selectedLabel);
    setInputValue(selectedLabel);
  }

  const query = useDebouncedValue(inputValue.trim(), DEBOUNCE_MS);
  // A digit means a ZIP prefix, which is useful from the first character
  const searchable = query.length >= MIN_QUERY_LENGTH || /^\d/.test(query);
  // Don't search again for the label the input shows after a selection
  const active = searchable && !(value !== null && query === value.label);

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    api
      .searchLocations(query, { signal: controller.signal })
      .then(({ results }) => setResponse({ query, results }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message = error instanceof ApiError ? error.message : "Location search failed.";
        setResponse((prev) => ({ query, results: prev?.results ?? [], error: message }));
      });
    return () => controller.abort();
  }, [query, active]);

  // Earlier results stay listed while the next search is in flight
  const results = useMemo(() => (searchable ? (response?.results ?? []) : []), [searchable, response]);
  // The selected value has to stay in `items` so the combobox can show it
  const items = useMemo<Location[]>(
    () => (value && !results.some((r) => r.id === value.id) ? [value, ...results] : results),
    [value, results],
  );

  const pending = inputValue.trim() !== query || (active && response?.query !== query);
  const error = active && response?.query === query ? response.error : undefined;
  const emptyMessage =
    error ??
    (pending
      ? "Searching…"
      : !searchable
        ? "Type a city name or ZIP code."
        : "No US city or ZIP code matches.");

  return (
    <Combobox
      items={items}
      filter={null}
      value={value}
      onValueChange={(v) => onChange(v)}
      inputValue={inputValue}
      onInputValueChange={setInputValue}
      itemToStringLabel={(l: Location) => l.label}
      isItemEqualToValue={(a: Location, b: Location) => a.id === b.id}
      autoHighlight
      disabled={disabled}
    >
      <ComboboxInput
        id={id}
        placeholder={placeholder}
        aria-invalid={invalid || undefined}
        onBlur={onBlur}
        showClear={value !== null}
        className="w-full"
      />
      <ComboboxContent>
        <ComboboxEmpty>
          {pending && <Spinner />}
          {emptyMessage}
        </ComboboxEmpty>
        <ComboboxList>
          {(item: Location) => (
            <ComboboxItem key={item.id} value={item}>
              {(item as LocationResult).type === "zip" ? (
                <Hash className="text-muted-foreground" />
              ) : (
                <MapPin className="text-muted-foreground" />
              )}
              {item.label}
            </ComboboxItem>
          )}
        </ComboboxList>
      </ComboboxContent>
    </Combobox>
  );
}

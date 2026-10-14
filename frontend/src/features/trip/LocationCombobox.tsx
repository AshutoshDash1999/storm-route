import { MapPin } from "lucide-react";

import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
} from "@/components/ui/combobox";
import type { Location } from "@/src/lib/types";
import { US_LOCATIONS } from "@/src/mock/us-locations";

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
  return (
    <Combobox
      items={US_LOCATIONS}
      value={value}
      onValueChange={(v) => onChange(v)}
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
        <ComboboxEmpty>No US location matches.</ComboboxEmpty>
        <ComboboxList>
          {(item: Location) => (
            <ComboboxItem key={item.id} value={item}>
              <MapPin className="text-muted-foreground" />
              {item.label}
            </ComboboxItem>
          )}
        </ComboboxList>
      </ComboboxContent>
    </Combobox>
  );
}

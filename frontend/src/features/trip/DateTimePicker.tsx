import { useState } from "react";
import { CalendarIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

const dateLabel = new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  month: "short",
  day: "numeric",
  year: "numeric",
});

function startOfToday() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

export function DateTimePicker({
  dateId,
  timeId,
  date,
  time,
  onDateChange,
  onTimeChange,
  dateInvalid,
  timeInvalid,
}: {
  dateId: string;
  timeId: string;
  date: Date | null;
  time: string;
  onDateChange: (d: Date | null) => void;
  onTimeChange: (t: string) => void;
  dateInvalid?: boolean;
  timeInvalid?: boolean;
}) {
  const [today] = useState(startOfToday);

  return (
    <div className="flex gap-2">
      <Popover>
        <PopoverTrigger
          render={
            <Button
              id={dateId}
              variant="outline"
              aria-invalid={dateInvalid || undefined}
              className="flex-1 justify-start font-normal"
            />
          }
        >
          <CalendarIcon className="text-muted-foreground" />
          {date ? dateLabel.format(date) : <span className="text-muted-foreground">Pick a date</span>}
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={date ?? undefined}
            onSelect={(d) => onDateChange(d ?? null)}
            disabled={{ before: today }}
            autoFocus
          />
        </PopoverContent>
      </Popover>
      <Input
        id={timeId}
        type="time"
        value={time}
        onChange={(e) => onTimeChange(e.target.value)}
        aria-invalid={timeInvalid || undefined}
        aria-label="Departure time"
        className="w-32 [&::-webkit-calendar-picker-indicator]:hidden"
      />
    </div>
  );
}

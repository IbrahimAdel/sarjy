import { Loader2, Mic, Volume2, Circle } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { AssistantState } from "@/types"

const CONFIG: Record<
  AssistantState,
  { label: string; variant: "default" | "secondary" | "outline"; icon: typeof Mic }
> = {
  listening: { label: "Listening", variant: "default", icon: Mic },
  thinking: { label: "Thinking", variant: "secondary", icon: Loader2 },
  speaking: { label: "Speaking", variant: "default", icon: Volume2 },
  idle: { label: "Idle", variant: "outline", icon: Circle },
}

export function StatusBadge({ state }: { state: AssistantState }) {
  const { label, variant, icon: Icon } = CONFIG[state]
  return (
    <Badge variant={variant} className="gap-1.5 py-1">
      <Icon
        className={cn("size-3", state === "thinking" && "animate-spin")}
        aria-hidden="true"
      />
      {label}
    </Badge>
  )
}

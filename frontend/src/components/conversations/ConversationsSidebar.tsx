import { Loader2, Plus, X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { formatRelativeTime } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { ConversationSummary } from "@/types"

interface ConversationsSidebarProps {
  items: ConversationSummary[]
  total: number
  activeId: string
  loading: boolean
  loadingMore: boolean
  error: string | null
  open: boolean
  onSelect: (id: string) => void
  onNew: () => void
  onLoadMore: () => void
  onReload: () => void
  onClose: () => void
}

function ConversationRow({
  conversation,
  active,
  onSelect,
}: {
  conversation: ConversationSummary
  active: boolean
  onSelect: (id: string) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(conversation.id)}
      aria-current={active ? "true" : undefined}
      className={cn(
        "flex flex-col gap-1 rounded-lg px-3 py-2 text-left transition-colors hover:bg-sidebar-accent",
        active && "bg-sidebar-accent"
      )}
    >
      <span className="truncate text-sm font-medium">{conversation.name}</span>
      <span className="truncate text-xs text-muted-foreground">
        {conversation.last_message}
      </span>
      <span className="flex items-center gap-2 text-xs text-muted-foreground">
        <Badge variant="secondary" className="capitalize">
          {conversation.last_message_role}
        </Badge>
        <span>{conversation.message_count} messages</span>
        <span className="ml-auto shrink-0">
          {formatRelativeTime(conversation.updated_at)}
        </span>
      </span>
    </button>
  )
}

export function ConversationsSidebar({
  items,
  total,
  activeId,
  loading,
  loadingMore,
  error,
  open,
  onSelect,
  onNew,
  onLoadMore,
  onReload,
  onClose,
}: ConversationsSidebarProps) {
  const isEmpty = !loading && error === null && items.length === 0

  return (
    <>
      {open ? (
        <div
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      ) : null}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r bg-sidebar text-sidebar-foreground transition-transform md:static md:z-auto md:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
        aria-label="Conversations"
      >
        <div className="flex items-center justify-between gap-2 border-b p-3">
          <h2 className="text-sm font-semibold">Conversations</h2>
          <div className="flex items-center gap-1">
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              onClick={onNew}
              aria-label="New conversation"
            >
              <Plus aria-hidden="true" />
            </Button>
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              onClick={onClose}
              aria-label="Close conversations"
              className="md:hidden"
            >
              <X aria-hidden="true" />
            </Button>
          </div>
        </div>

        <ScrollArea className="flex-1">
          <div className="flex flex-col gap-1 p-2">
            {loading && items.length === 0 ? (
              <div className="flex items-center justify-center py-8 text-muted-foreground">
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                <span className="sr-only">Loading conversations</span>
              </div>
            ) : null}

            {error !== null && items.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-center text-sm text-muted-foreground">
                <span>{error}</span>
                <Button type="button" size="sm" variant="outline" onClick={onReload}>
                  Retry
                </Button>
              </div>
            ) : null}

            {isEmpty ? (
              <p className="px-3 py-8 text-center text-sm text-muted-foreground">
                No conversations yet. Start talking to create one.
              </p>
            ) : null}

            {items.map((conversation) => (
              <ConversationRow
                key={conversation.id}
                conversation={conversation}
                active={conversation.id === activeId}
                onSelect={onSelect}
              />
            ))}
          </div>
        </ScrollArea>

        {items.length < total ? (
          <div className="border-t p-2">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="w-full"
              onClick={onLoadMore}
              disabled={loadingMore}
            >
              {loadingMore ? (
                <Loader2 className="animate-spin" aria-hidden="true" />
              ) : null}
              Load more
            </Button>
          </div>
        ) : null}
      </aside>
    </>
  )
}

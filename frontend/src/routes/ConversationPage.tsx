import { useCallback, useEffect, useState } from "react"
import { LogOut, Menu } from "lucide-react"
import { useNavigate } from "react-router-dom"

import { ConversationsSidebar } from "@/components/conversations/ConversationsSidebar"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { VoiceConsole } from "@/components/voice/VoiceConsole"
import { useAuth } from "@/hooks/useAuth"
import { useConversations } from "@/hooks/useConversations"
import {
  createConversationId,
  readActiveConversationId,
  storeActiveConversationId,
} from "@/lib/conversation"

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) {
    return "?"
  }
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("")
}

export function ConversationPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [activeId, setActiveId] = useState(
    () => readActiveConversationId() ?? createConversationId()
  )
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    storeActiveConversationId(activeId)
  }, [activeId])
  const {
    items: conversations,
    total: conversationTotal,
    loading: conversationsLoading,
    loadingMore: conversationsLoadingMore,
    error: conversationsError,
    loadMore: loadMoreConversations,
    reload: reloadConversations,
  } = useConversations()

  const handleLogout = () => {
    logout()
    navigate("/login", { replace: true })
  }

  const handleSelect = (id: string) => {
    storeActiveConversationId(id)
    setActiveId(id)
    setSidebarOpen(false)
  }

  const handleNew = () => {
    const id = createConversationId()
    storeActiveConversationId(id)
    setActiveId(id)
    setSidebarOpen(false)
  }

  const handleSessionEnd = useCallback(() => {
    void reloadConversations()
  }, [reloadConversations])

  return (
    <div className="flex h-screen overflow-hidden">
      <ConversationsSidebar
        items={conversations}
        total={conversationTotal}
        activeId={activeId}
        loading={conversationsLoading}
        loadingMore={conversationsLoadingMore}
        error={conversationsError}
        open={sidebarOpen}
        onSelect={handleSelect}
        onNew={handleNew}
        onLoadMore={loadMoreConversations}
        onReload={() => void reloadConversations()}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-2 border-b p-4">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              className="md:hidden"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open conversations"
            >
              <Menu aria-hidden="true" />
            </Button>
            <div>
              <h1 className="text-lg font-semibold">Sarjy</h1>
              <p className="text-sm text-muted-foreground">Voice assistant</p>
            </div>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger className="rounded-full outline-none">
              <Avatar>
                <AvatarFallback>{initials(user?.name ?? "")}</AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>
                <span className="block font-medium text-foreground">
                  {user?.name}
                </span>
                <span className="block">{user?.email}</span>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive" onClick={handleLogout}>
                <LogOut aria-hidden="true" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        <div className="min-h-0 flex-1 p-4">
          <VoiceConsole
            conversationId={activeId}
            onSessionEnd={handleSessionEnd}
          />
        </div>
      </main>
    </div>
  )
}

import { Loader2 } from "lucide-react"
import { Navigate, Outlet } from "react-router-dom"

import { useAuth } from "@/hooks/useAuth"

export function ProtectedRoute() {
  const { status } = useAuth()

  if (status === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
        <span className="sr-only">Loading</span>
      </main>
    )
  }

  if (status === "anonymous") {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}

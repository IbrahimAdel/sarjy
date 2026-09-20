import { Link, Navigate, useNavigate } from "react-router-dom"

import { AuthLayout } from "@/components/auth/AuthLayout"
import { LoginForm } from "@/components/auth/LoginForm"
import { useAuth } from "@/hooks/useAuth"

export function LoginPage() {
  const { status } = useAuth()
  const navigate = useNavigate()

  if (status === "authenticated") {
    return <Navigate to="/" replace />
  }

  return (
    <AuthLayout
      title="Welcome back"
      description="Sign in to start talking with Sarjy."
      footer={
        <>
          No account?{" "}
          <Link to="/register" className="font-medium text-foreground underline">
            Create one
          </Link>
        </>
      }
    >
      <LoginForm onSuccess={() => navigate("/", { replace: true })} />
    </AuthLayout>
  )
}

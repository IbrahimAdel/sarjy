import { Link, Navigate, useNavigate } from "react-router-dom"

import { AuthLayout } from "@/components/auth/AuthLayout"
import { RegisterForm } from "@/components/auth/RegisterForm"
import { useAuth } from "@/hooks/useAuth"

export function RegisterPage() {
  const { status } = useAuth()
  const navigate = useNavigate()

  if (status === "authenticated") {
    return <Navigate to="/" replace />
  }

  return (
    <AuthLayout
      title="Create your account"
      description="Register to start having voice conversations."
      footer={
        <>
          Already registered?{" "}
          <Link to="/login" className="font-medium text-foreground underline">
            Sign in
          </Link>
        </>
      }
    >
      <RegisterForm onSuccess={() => navigate("/", { replace: true })} />
    </AuthLayout>
  )
}

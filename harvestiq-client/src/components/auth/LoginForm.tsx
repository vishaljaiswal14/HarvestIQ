"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { loginSchema, type LoginFormValues } from "@/lib/validations";
import { useAuthStore } from "@/stores/authStore";
import { useTranslation } from "@/stores/localizationStore";

export function LoginForm() {
  const router = useRouter();
  const { t } = useTranslation();
  const login = useAuthStore((state) => state.login);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      phone: "",
      password: "",
    },
  });

  const onSubmit = async (values: LoginFormValues) => {
    setError(null);
    try {
      await login(values.phone, values.password);
      const user = useAuthStore.getState().user;
      router.push(user?.onboarding_completed ? "/" : "/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.loginFailed", "Login failed"));
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="login-phone">{t("auth.phoneLabel", "Phone")}</Label>
        <Input
          id="login-phone"
          placeholder="+919876543210"
          autoComplete="tel"
          {...register("phone")}
        />
        {errors.phone && (
          <p className="text-sm text-red-600">{t(errors.phone.message || "", errors.phone.message)}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="login-password">{t("auth.passwordLabel", "Password")}</Label>
        <Input
          id="login-password"
          type="password"
          autoComplete="current-password"
          {...register("password")}
        />
        {errors.password && (
          <p className="text-sm text-red-600">{t(errors.password.message || "", errors.password.message)}</p>
        )}
      </div>

      {error && <p className="text-sm text-red-600">{t(error, error)}</p>}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? t("auth.signingIn", "Signing in...") : t("auth.signIn", "Sign in")}
      </Button>
    </form>
  );
}

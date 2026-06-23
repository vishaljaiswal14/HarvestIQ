"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { registerSchema, type RegisterFormValues } from "@/lib/validations";
import { useAuthStore } from "@/stores/authStore";
import { useTranslation } from "@/stores/localizationStore";

type RegisterFormProps = {
  onRegistered: () => void;
};

export function RegisterForm({ onRegistered }: RegisterFormProps) {
  const { t } = useTranslation();
  const registerUser = useAuthStore((state) => state.register);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: "",
      phone: "",
      password: "",
      preferred_lang: "hi",
    },
  });

  const onSubmit = async (values: RegisterFormValues) => {
    setError(null);
    setSuccess(null);
    try {
      await registerUser(
        values.name,
        values.phone,
        values.password,
        values.preferred_lang,
      );
      setSuccess(t("auth.registrationSuccess", "Account created. Switch to Sign in to continue."));
      onRegistered();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.registrationFailed", "Registration failed"));
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="register-name">{t("auth.nameLabel", "Name")}</Label>
        <Input id="register-name" autoComplete="name" {...register("name")} />
        {errors.name && (
          <p className="text-sm text-red-600">{t(errors.name.message || "", errors.name.message)}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="register-phone">{t("auth.phoneLabel", "Phone")}</Label>
        <Input
          id="register-phone"
          placeholder="+919876543210"
          autoComplete="tel"
          {...register("phone")}
        />
        {errors.phone && (
          <p className="text-sm text-red-600">{t(errors.phone.message || "", errors.phone.message)}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="register-password">{t("auth.passwordLabel", "Password")}</Label>
        <Input
          id="register-password"
          type="password"
          autoComplete="new-password"
          {...register("password")}
        />
        {errors.password && (
          <p className="text-sm text-red-600">{t(errors.password.message || "", errors.password.message)}</p>
        )}
      </div>

      {error && <p className="text-sm text-red-600">{t(error, error)}</p>}
      {success && <p className="text-sm text-emerald-700">{success}</p>}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? t("auth.creatingAccount", "Creating account...") : t("auth.createAccountBtn", "Create account")}
      </Button>
    </form>
  );
}

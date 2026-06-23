"use client";

import { useState } from "react";

import { AuthGuard } from "@/components/AuthGuard";
import { LoginForm } from "@/components/auth/LoginForm";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { AuthBrandLayout } from "@/components/layout/AuthBrandLayout";
import { InstallPwaButton } from "@/components/InstallPwaButton";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useTranslation } from "@/stores/localizationStore";

function AuthPageContent() {
  const { t } = useTranslation();
  const [tab, setTab] = useState("login");

  return (
    <AuthBrandLayout
      title={tab === "login" ? t("auth.welcomeBack", "Welcome back") : t("auth.createAccount", "Create your account")}
      description={t("auth.pageDesc", "Sign in or register to access your field intelligence dashboard.")}
    >
      <div className="mb-3 flex justify-end">
        <InstallPwaButton />
      </div>
      <Card className="dashboard-card border-emerald-100/80 shadow-md">
        <CardContent className="pt-6">
          <Tabs value={tab} onValueChange={setTab}>
            <TabsList className="grid h-11 w-full grid-cols-2">
              <TabsTrigger value="login" className="min-h-[44px]">{t("auth.signIn", "Sign in")}</TabsTrigger>
              <TabsTrigger value="register" className="min-h-[44px]">{t("auth.register", "Register")}</TabsTrigger>
            </TabsList>
            <TabsContent value="login" className="mt-4">
              <LoginForm />
            </TabsContent>
            <TabsContent value="register" className="mt-4">
              <RegisterForm onRegistered={() => setTab("login")} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </AuthBrandLayout>
  );
}

export default function AuthPage() {
  return (
    <AuthGuard redirectIfAuthenticated>
      <AuthPageContent />
    </AuthGuard>
  );
}

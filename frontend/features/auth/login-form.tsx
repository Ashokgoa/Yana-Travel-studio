"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { controlClass, errorProps, FormField } from "@/components/common/form-controls";
import { useAuth } from "@/features/auth/auth-provider";
import { ApiError } from "@/services/api";

const schema = z.object({
  email: z.string().trim().min(1, "Enter your email").email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});
type Values = z.infer<typeof schema>;

/** Only allow redirects to in-app paths (no open redirects). */
function safeNext(next: string | null) {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}

export function LoginForm() {
  const { login, user } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, formState } = useForm<Values>({ resolver: zodResolver(schema) });
  const { errors, isSubmitting } = formState;

  useEffect(() => {
    if (user) router.replace(safeNext(params.get("next")));
  }, [user, router, params]);

  const onSubmit = async (values: Values) => {
    setFormError(null);
    try {
      await login(values.email, values.password);
      router.replace(safeNext(params.get("next")));
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "Sign in failed. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      {formError && (
        <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2.5 text-sm text-destructive">
          {formError}
        </div>
      )}
      <FormField label="Email" htmlFor="email" error={errors.email?.message}>
        <input id="email" type="email" autoComplete="username" autoFocus className={controlClass} {...errorProps("email", errors.email?.message)} {...register("email")} />
      </FormField>
      <FormField label="Password" htmlFor="password" error={errors.password?.message}>
        <input id="password" type="password" autoComplete="current-password" className={controlClass} {...errorProps("password", errors.password?.message)} {...register("password")} />
      </FormField>
      <Button type="submit" className="h-10 w-full" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="animate-spin" aria-hidden />}
        Sign in
      </Button>
    </form>
  );
}

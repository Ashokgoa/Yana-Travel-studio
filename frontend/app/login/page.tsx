import type { Metadata } from "next";
import { Suspense } from "react";
import { LoginForm } from "@/features/auth/login-form";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <aside className="relative hidden overflow-hidden bg-primary p-12 text-primary-foreground lg:flex lg:flex-col">
        <div aria-hidden className="pointer-events-none absolute -top-32 -left-24 size-[28rem] rounded-full bg-brand-teal/40 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute -right-20 bottom-0 size-80 rounded-full bg-brand-gold/25 blur-3xl" />
        <div className="relative">
          <p className="font-heading text-2xl font-semibold tracking-wide">YANA</p>
          <p className="text-xs font-medium uppercase tracking-[0.25em] text-brand-gold">Travel Studio</p>
        </div>
        <div className="relative mt-auto max-w-md">
          <h2 className="text-4xl leading-tight font-semibold">Tailored European journeys, proposed in minutes.</h2>
          <p className="mt-4 text-primary-foreground/70">
            Capture agent requirements, build itineraries from your own inventory and send branded proposals.
          </p>
        </div>
      </aside>
      <main className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <p className="font-heading text-2xl font-semibold">YANA</p>
            <p className="text-xs font-medium uppercase tracking-[0.25em] text-brand-teal">Travel Studio</p>
          </div>
          <h1 className="text-2xl font-semibold">Sign in</h1>
          <p className="mt-1 mb-8 text-sm text-muted-foreground">Use the account your administrator created for you.</p>
          <Suspense>
            <LoginForm />
          </Suspense>
        </div>
      </main>
    </div>
  );
}

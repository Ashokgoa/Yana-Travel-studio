"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { z } from "zod";
import { Pencil, Plus, UserCog } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { controlClass, errorProps, FormField, NativeSelect } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states";
import { ActiveBadge } from "@/components/common/status-badge";
import { useAuth } from "@/features/auth/auth-provider";
import { formatDate } from "@/lib/format";
import { handleFormError } from "@/lib/form-errors";
import { usersApi } from "@/services/crm";
import type { User } from "@/types/crm";

const ROLE_HELP = {
  admin: "Manages inventory, suppliers, templates, pricing settings and users.",
  planner: "Handles enquiries, itineraries and proposals.",
};

const createSchema = z.object({
  full_name: z.string().trim().min(1, "Name is required").max(200),
  email: z.email("Enter a valid email address"),
  role: z.enum(["admin", "planner"]),
  password: z.string().min(8, "At least 8 characters").max(128),
});
const editSchema = z.object({
  full_name: z.string().trim().min(1, "Name is required").max(200),
  email: z.string(),
  role: z.enum(["admin", "planner"]),
  password: z.union([z.literal(""), z.string().min(8, "At least 8 characters").max(128)]),
  is_active: z.enum(["true", "false"]),
});
type Values = z.infer<typeof editSchema>;

function UserDialog({ open, onOpenChange, user }: { open: boolean; onOpenChange: (o: boolean) => void; user?: User }) {
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, setError, formState } = useForm<Values>({
    // Same field set for both modes; creation additionally requires email + password.
    resolver: zodResolver((user ? editSchema : createSchema.extend({ is_active: z.enum(["true", "false"]) })) as typeof editSchema),
  });
  const { errors } = formState;

  useEffect(() => {
    if (open) {
      reset({
        full_name: user?.full_name ?? "",
        email: user?.email ?? "",
        role: user?.role.code ?? "planner",
        password: "",
        is_active: user?.is_active === false ? "false" : "true",
      });
    }
  }, [open, user, reset]);

  const mutation = useMutation({
    mutationFn: (v: Values) =>
      user
        ? usersApi.update(user.id, {
            full_name: v.full_name,
            role: v.role,
            is_active: v.is_active === "true",
            ...(v.password ? { password: v.password } : {}),
          })
        : usersApi.create({ full_name: v.full_name, email: v.email, role: v.role, password: v.password }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success(user ? "User updated" : "User created");
      onOpenChange(false);
    },
    onError: (e) => handleFormError(e, setError, ["full_name", "email", "role", "password"]),
  });

  const f = (name: keyof Values) => ({ id: `user-${name}`, ...errorProps(`user-${name}`, errors[name]?.message), ...register(name) });

  return (
    <FormDialog
      open={open}
      onOpenChange={onOpenChange}
      title={user ? `Edit ${user.full_name}` : "New user"}
      description={user ? undefined : "Share the email and initial password with the user; they can be changed later."}
      formId="user-form"
      submitLabel={user ? "Save changes" : "Create user"}
      pending={mutation.isPending}
    >
      <form id="user-form" noValidate onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
        <FormField label="Full name" htmlFor="user-full_name" required error={errors.full_name?.message}>
          <input className={controlClass} autoFocus {...f("full_name")} />
        </FormField>
        <FormField label="Email" htmlFor="user-email" required={!user} error={errors.email?.message} hint={user ? "Email can't be changed." : undefined}>
          <input type="email" className={controlClass} disabled={!!user} {...f("email")} />
        </FormField>
        <FormField label="Role" htmlFor="user-role" required>
          <NativeSelect {...f("role")}>
            <option value="planner">Travel Planner: {ROLE_HELP.planner}</option>
            <option value="admin">Administrator: {ROLE_HELP.admin}</option>
          </NativeSelect>
        </FormField>
        <FormField
          label={user ? "New password" : "Initial password"}
          htmlFor="user-password"
          required={!user}
          error={errors.password?.message}
          hint={user ? "Leave blank to keep the current password." : "At least 8 characters."}
        >
          <input type="password" autoComplete="new-password" className={controlClass} {...f("password")} />
        </FormField>
        {user && (
          <FormField label="Status" htmlFor="user-is_active">
            <NativeSelect {...f("is_active")}>
              <option value="true">Active: can sign in</option>
              <option value="false">Inactive: cannot sign in</option>
            </NativeSelect>
          </FormField>
        )}
      </form>
    </FormDialog>
  );
}

export function UsersAdmin() {
  const { user: me } = useAuth();
  const users = useQuery({ queryKey: ["users", "list"], queryFn: () => usersApi.list() });
  const [editing, setEditing] = useState<User | undefined>();
  const [open, setOpen] = useState(false);

  return (
    <>
      <PageHeader
        title="Users"
        description="Who can sign in to YANA Travel Studio, and what they can do."
        actions={
          <Button onClick={() => { setEditing(undefined); setOpen(true); }}>
            <Plus aria-hidden /> New user
          </Button>
        }
      />
      <Card className="p-4 sm:p-5">
        {users.isPending ? (
          <TableSkeleton />
        ) : users.isError ? (
          <ErrorState message={users.error.message} onRetry={() => users.refetch()} />
        ) : users.data.length === 0 ? (
          <EmptyState icon={UserCog} title="No users" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Role</TableHead>
                <TableHead className="hidden md:table-cell">Created</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-12"><span className="sr-only">Actions</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.data.map((u) => (
                <TableRow key={u.id}>
                  <TableCell>
                    <div className="font-medium">{u.full_name}{u.id === me?.id && <span className="ml-2 text-xs text-muted-foreground">(you)</span>}</div>
                    <div className="text-xs text-muted-foreground">{u.email}</div>
                  </TableCell>
                  <TableCell>{u.role.name}</TableCell>
                  <TableCell className="hidden md:table-cell">{formatDate(u.created_at)}</TableCell>
                  <TableCell><ActiveBadge status={u.is_active} /></TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon" aria-label={`Edit ${u.full_name}`} onClick={() => { setEditing(u); setOpen(true); }}>
                      <Pencil />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
      <UserDialog open={open} onOpenChange={setOpen} user={editing} />
    </>
  );
}

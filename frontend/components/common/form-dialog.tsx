"use client";

import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

/** Modal shell for create/edit forms. The form element inside must use id={formId}. */
export function FormDialog({
  open,
  onOpenChange,
  title,
  description,
  formId,
  submitLabel = "Save",
  pending,
  wide,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  formId: string;
  submitLabel?: string;
  pending?: boolean;
  wide?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Dialog open={open} onOpenChange={(next) => !pending && onOpenChange(next)}>
      <DialogContent className={cn("max-h-[92vh] gap-0 overflow-hidden p-0", wide ? "sm:max-w-2xl" : "sm:max-w-lg")}>
        <DialogHeader className="border-b px-6 pt-6 pb-4">
          <DialogTitle className="font-heading text-xl">{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <div className="max-h-[calc(92vh-10rem)] overflow-y-auto px-6 py-5">{children}</div>
        <DialogFooter className="m-0 border-t px-6 py-4">
          <Button variant="outline" type="button" onClick={() => onOpenChange(false)} disabled={pending}>
            Cancel
          </Button>
          <Button type="submit" form={formId} disabled={pending}>
            {pending && <Loader2 className="animate-spin" aria-hidden />}
            {submitLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

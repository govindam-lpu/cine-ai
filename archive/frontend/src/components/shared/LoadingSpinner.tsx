import { cn } from "@/lib/utils";

type LoadingSpinnerProps = {
  className?: string;
  label?: string;
};

export default function LoadingSpinner({ className, label = "Loading" }: LoadingSpinnerProps) {
  return (
    <div className={cn("flex items-center gap-3 text-sm text-text-secondary", className)}>
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-border-default border-t-accent" />
      <span>{label}</span>
    </div>
  );
}

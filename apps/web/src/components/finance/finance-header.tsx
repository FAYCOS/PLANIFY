import { Button } from "@/components/ui/button";

type FinanceHeaderProps = {
  title: string;
  subtitle?: string;
  primaryAction?: React.ReactNode;
};

export function FinanceHeader({ title, subtitle, primaryAction }: FinanceHeaderProps) {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <h1 className="text-2xl font-semibold">{title}</h1>
        {subtitle ? (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        ) : null}
      </div>
      {primaryAction ? <Button asChild>{primaryAction}</Button> : null}
    </div>
  );
}

import { DashboardMetrics } from "@/components/dashboard/metrics";
import { FinanceChartPlaceholder } from "@/components/dashboard/finance-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Bienvenue sur Planify</h1>
        <p className="text-sm text-muted-foreground">
          Suivez vos operations, votre materiel et votre finance.
        </p>
      </div>

      <DashboardMetrics />

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <FinanceChartPlaceholder />
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Alertes & a faire
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="rounded-lg border border-dashed p-3">
              3 devis a relancer cette semaine.
            </div>
            <div className="rounded-lg border border-dashed p-3">
              2 missions a confirmer.
            </div>
            <div className="rounded-lg border border-dashed p-3">
              1 paiement en attente de rapprochement.
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

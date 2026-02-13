export const dynamic = "force-dynamic";

import Link from "next/link";

import { desc, eq } from "drizzle-orm";

import { db } from "@/db";
import { facture } from "@/db/schema";
import { FinanceHeader } from "@/components/finance/finance-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getServerSession } from "@/lib/auth-session";
import { redirect } from "next/navigation";

function formatEuro(value: string | null) {
  const number = Number(value ?? "0");
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 2,
  }).format(number);
}

export default async function FacturesPage({
  searchParams,
}: {
  searchParams?: { q?: string; statut?: string };
}) {
  const q = searchParams?.q?.toLowerCase() ?? "";
  const statut = searchParams?.statut ?? "";
  const session = await getServerSession();
  const orgId = session?.user?.orgId;
  if (!orgId) {
    redirect("/signup");
  }
  const factures = await db
    .select()
    .from(facture)
    .where(eq(facture.orgId, orgId))
    .orderBy(desc(facture.dateCreation))
    .limit(200);
  return (
    <div className="space-y-6">
      <FinanceHeader
        title="Factures"
        subtitle="Pilotez vos factures et encaissements"
        primaryAction={
          <Link href="/finance/factures/nouveau">Nouvelle facture</Link>
        }
      />
      <Card>
        <CardContent className="pt-6">
          <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <form className="flex flex-1 gap-2">
              <input
                name="q"
                defaultValue={q}
                placeholder="Rechercher..."
                className="w-full rounded-md border border-border bg-white px-3 py-2 text-sm"
              />
              <select
                name="statut"
                defaultValue={statut}
                className="rounded-md border border-border bg-white px-3 py-2 text-sm"
              >
                <option value="">Tous</option>
                <option value="brouillon">Brouillon</option>
                <option value="envoye">Envoye</option>
                <option value="paye">Paye</option>
              </select>
            </form>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Numero</TableHead>
                <TableHead>Client</TableHead>
                <TableHead>Date</TableHead>
                <TableHead className="text-right">Montant</TableHead>
                <TableHead>Statut</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {factures
                .filter((row) => {
                  if (statut && row.statut !== statut) return false;
                  if (!q) return true;
                  return (
                    row.numero.toLowerCase().includes(q) ||
                    row.clientNom.toLowerCase().includes(q)
                  );
                })
                .map((row) => (
                  <TableRow key={row.numero}>
                    <TableCell>
                      <Link
                        href={`/finance/factures/${row.id}`}
                        className="text-primary hover:underline"
                      >
                        {row.numero}
                      </Link>
                    </TableCell>
                    <TableCell>{row.clientNom}</TableCell>
                    <TableCell>
                      {row.dateCreation
                        ? new Date(row.dateCreation).toLocaleDateString("fr-FR")
                        : "-"}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatEuro(row.montantTtc?.toString() ?? "0")}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={row.statut === "paye" ? "success" : "warning"}
                      >
                        {row.statut}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

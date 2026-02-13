export const dynamic = "force-dynamic";

import Link from "next/link";
import { type SearchParams } from "next/dist/server/request/search-params";

import { desc, eq, inArray } from "drizzle-orm";

import { db } from "@/db";
import { client, clientContact, devis, facture } from "@/db/schema";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getServerSession } from "@/lib/auth-session";
import { redirect } from "next/navigation";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type PageProps = {
  searchParams?: SearchParams;
};

export default async function ClientsPage({ searchParams }: PageProps) {
  const q = typeof searchParams?.q === "string" ? searchParams.q : "";
  const session = await getServerSession();
  const orgId = session?.user?.orgId;
  if (!orgId) {
    redirect("/signup");
  }
  const clients = await db
    .select()
    .from(client)
    .where(eq(client.orgId, orgId))
    .orderBy(desc(client.createdAt))
    .limit(200);

  const clientIds = clients.map((row) => row.id);
  const contacts = clientIds.length
    ? await db
        .select()
        .from(clientContact)
        .where(inArray(clientContact.clientId, clientIds))
    : [];
  const devisRows = clientIds.length
    ? await db
        .select()
        .from(devis)
        .where(inArray(devis.clientId, clientIds))
    : [];
  const factureRows = clientIds.length
    ? await db
        .select()
        .from(facture)
        .where(inArray(facture.clientId, clientIds))
    : [];

  const contactCount = new Map<string, number>();
  for (const row of contacts) {
    contactCount.set(row.clientId, (contactCount.get(row.clientId) || 0) + 1);
  }

  const devisCount = new Map<string, number>();
  for (const row of devisRows) {
    if (!row.clientId) continue;
    devisCount.set(row.clientId, (devisCount.get(row.clientId) || 0) + 1);
  }

  const factureCount = new Map<string, number>();
  for (const row of factureRows) {
    if (!row.clientId) continue;
    factureCount.set(row.clientId, (factureCount.get(row.clientId) || 0) + 1);
  }
  return (
    <Card>
      <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <CardTitle>Clients</CardTitle>
          <p className="text-sm text-muted-foreground">
            Retrouvez vos clients et leurs documents associes.
          </p>
        </div>
        <div className="flex w-full flex-col gap-2 md:w-auto md:flex-row md:items-center">
          <form className="w-full md:w-64">
            <input
              name="q"
              defaultValue={q}
              placeholder="Rechercher..."
              className="w-full rounded-md border border-border bg-white px-3 py-2 text-sm"
            />
          </form>
          <Button asChild>
            <Link href="/clients/nouveau">Nouveau client</Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nom</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Telephone</TableHead>
              <TableHead>Contacts</TableHead>
              <TableHead>Factures</TableHead>
              <TableHead>Devis</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {clients
              .filter((row) => {
                if (!q) return true;
                const needle = q.toLowerCase();
                return (
                  row.nom.toLowerCase().includes(needle) ||
                  (row.prenom ?? "").toLowerCase().includes(needle) ||
                  (row.email ?? "").toLowerCase().includes(needle) ||
                  (row.telephone ?? "").toLowerCase().includes(needle)
                );
              })
              .map((row) => (
              <TableRow key={row.id}>
                <TableCell className="font-medium">
                  <Link
                    href={`/clients/${row.id}`}
                    className="text-primary hover:underline"
                  >
                    {[row.prenom, row.nom].filter(Boolean).join(" ") || row.nom}
                  </Link>
                </TableCell>
                <TableCell>{row.email ?? "-"}</TableCell>
                <TableCell>{row.telephone ?? "-"}</TableCell>
                <TableCell>{contactCount.get(row.id) || 0}</TableCell>
                <TableCell>{factureCount.get(row.id) || 0}</TableCell>
                <TableCell>{devisCount.get(row.id) || 0}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

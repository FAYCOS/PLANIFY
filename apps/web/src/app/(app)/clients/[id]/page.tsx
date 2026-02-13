export const dynamic = "force-dynamic";

import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { and, desc, eq } from "drizzle-orm";

import { db } from "@/db";
import { client, clientContact, devis, facture, prestation } from "@/db/schema";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getServerSession } from "@/lib/auth-session";

type Params = { params: Promise<{ id: string }> };

export default async function ClientDetailPage({ params }: Params) {
  const { id } = await params;
  const session = await getServerSession();
  const orgId = session?.user?.orgId;
  if (!orgId) {
    redirect("/signup");
  }
  const [row] = await db
    .select()
    .from(client)
    .where(and(eq(client.id, id), eq(client.orgId, orgId)))
    .limit(1);
  if (!row) notFound();

  const contacts = await db
    .select()
    .from(clientContact)
    .where(eq(clientContact.clientId, id));
  const devisRows = await db
    .select()
    .from(devis)
    .where(and(eq(devis.clientId, id), eq(devis.orgId, orgId)))
    .orderBy(desc(devis.dateCreation));
  const factureRows = await db
    .select()
    .from(facture)
    .where(and(eq(facture.clientId, id), eq(facture.orgId, orgId)))
    .orderBy(desc(facture.dateCreation));
  const missions = await db
    .select()
    .from(prestation)
    .where(and(eq(prestation.clientId, id), eq(prestation.orgId, orgId)))
    .orderBy(desc(prestation.createdAt));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            {[row.prenom, row.nom].filter(Boolean).join(" ") || row.nom}
          </h1>
          <p className="text-sm text-muted-foreground">{row.email ?? "-"}</p>
        </div>
        <Button asChild>
          <Link href={`/clients/${row.id}/modifier`}>Modifier</Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Informations</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm">
          <div>Telephone: {row.telephone ?? "-"}</div>
          <div>Adresse: {row.adresseFacturation ?? "-"}</div>
          <div>Categories: {row.categories ?? "-"}</div>
          <div>Notes: {row.notes ?? "-"}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Contacts</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {contacts.length === 0 ? (
            <div className="text-muted-foreground">Aucun contact.</div>
          ) : (
            contacts.map((contact) => (
              <div key={contact.id} className="rounded-md border p-2">
                <div className="font-medium">{contact.nom}</div>
                <div className="text-muted-foreground">
                  {contact.email ?? "-"} · {contact.telephone ?? "-"}
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Devis</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {devisRows.slice(0, 5).map((item) => (
              <div key={item.id} className="flex justify-between">
                <span>{item.numero}</span>
                <span className="text-muted-foreground">{item.statut}</span>
              </div>
            ))}
            {devisRows.length === 0 ? (
              <div className="text-muted-foreground">Aucun devis.</div>
            ) : null}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Factures</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {factureRows.slice(0, 5).map((item) => (
              <div key={item.id} className="flex justify-between">
                <span>{item.numero}</span>
                <span className="text-muted-foreground">{item.statut}</span>
              </div>
            ))}
            {factureRows.length === 0 ? (
              <div className="text-muted-foreground">Aucune facture.</div>
            ) : null}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Missions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {missions.slice(0, 5).map((item) => (
              <div key={item.id} className="flex justify-between">
                <span>{item.id.slice(0, 8)}</span>
                <span className="text-muted-foreground">{item.statut}</span>
              </div>
            ))}
            {missions.length === 0 ? (
              <div className="text-muted-foreground">Aucune mission.</div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

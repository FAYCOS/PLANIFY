/* eslint-disable @typescript-eslint/no-explicit-any */
import "dotenv/config";
import Database from "better-sqlite3";
import { randomUUID } from "crypto";
import { sql } from "drizzle-orm";

import { db, dbForSchema } from "../src/db";
import { buildSearchPathUrl, createSchemaForOrg } from "../src/lib/signup";
import {
  organization,
  user,
  client,
  clientContact,
  prestation,
  devis,
  facture,
  paiement,
  avoir,
  materiel,
  materielPrestation,
  mouvementMateriel,
  parametresEntreprise,
  documentSequence,
  prestationRating,
} from "../src/db/schema";

type AnyRow = Record<string, any>;

const SQLITE_PATH =
  process.env.SQLITE_PATH || "../../instance/dj_prestations.db";

const sqlite = new Database(SQLITE_PATH, { readonly: true });

function toDate(value: any): string | null {
  if (!value) return null;
  if (value instanceof Date) {
    return value.toISOString().slice(0, 10);
  }
  const str = String(value);
  return str.length >= 10 ? str.slice(0, 10) : str;
}

function toDateTime(value: any): Date | null {
  if (!value) return null;
  if (value instanceof Date) return value;
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? null : parsed;
}

function parseJson(value: any) {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

async function resetDatabase() {
  if (process.env.RESET_DB !== "1") return;
  await db.execute(sql`
    TRUNCATE TABLE
      prestation_ratings,
      mouvements_materiel,
      materiels_prestations,
      materiels,
      avoirs,
      paiements,
      factures,
      devis,
      prestations,
      client_contacts,
      clients,
      document_sequences,
      parametres_entreprise,
      account,
      session,
      verification,
      "user",
      organizations
    CASCADE
  `);
}

async function main() {
  await resetDatabase();

  const orgId = randomUUID();
  const schemaName = `org_${orgId.replace(/-/g, "").slice(0, 12)}`;
  await db.insert(organization).values({ id: orgId, name: "Planify", dbSchema: schemaName });
  const baseUrl = process.env.DATABASE_URL;
  if (baseUrl) {
    await db
      .update(organization)
      .set({ dbUrl: buildSearchPathUrl(baseUrl, schemaName) })
      .where(sql`id = ${orgId}`);
  }
  await createSchemaForOrg(schemaName);
  const tenantDb = dbForSchema(schemaName);

  const userRows = sqlite.prepare("SELECT * FROM users").all() as AnyRow[];
  const djRows = sqlite.prepare("SELECT * FROM djs").all() as AnyRow[];
  const clientRows = sqlite.prepare("SELECT * FROM clients").all() as AnyRow[];
  const contactRows = sqlite
    .prepare("SELECT * FROM client_contacts")
    .all() as AnyRow[];
  const prestationRows = sqlite
    .prepare("SELECT * FROM prestations")
    .all() as AnyRow[];
  const devisRows = sqlite.prepare("SELECT * FROM devis").all() as AnyRow[];
  const factureRows = sqlite.prepare("SELECT * FROM factures").all() as AnyRow[];
  const paiementRows = sqlite.prepare("SELECT * FROM paiements").all() as AnyRow[];
  const avoirRows = sqlite.prepare("SELECT * FROM avoirs").all() as AnyRow[];
  const materielRows = sqlite.prepare("SELECT * FROM materiels").all() as AnyRow[];
  const materielPrestaRows = sqlite
    .prepare("SELECT * FROM materiel_presta")
    .all() as AnyRow[];
  const mouvementRows = sqlite
    .prepare("SELECT * FROM mouvements_materiel")
    .all() as AnyRow[];
  const paramRows = sqlite
    .prepare("SELECT * FROM parametres_entreprise")
    .all() as AnyRow[];
  const sequenceRows = sqlite
    .prepare("SELECT * FROM document_sequences")
    .all() as AnyRow[];
  const ratingRows = sqlite
    .prepare("SELECT * FROM prestation_ratings")
    .all() as AnyRow[];

  const userMap = new Map<number, string>();
  const djMap = new Map<number, string>();
  const clientMap = new Map<number, string>();
  const prestationMap = new Map<number, string>();
  const devisMap = new Map<number, string>();
  const factureMap = new Map<number, string>();
  const materielMap = new Map<number, string>();

  const usersToInsert = userRows.map((row) => {
    const id = randomUUID();
    userMap.set(row.id, id);
    return {
      id,
      orgId,
      email: row.email,
      emailVerified: true,
      name: `${row.prenom || ""} ${row.nom || ""}`.trim() || row.username,
      role: row.role || "dj",
      nom: row.nom || null,
      prenom: row.prenom || null,
      telephone: row.telephone || null,
      createdAt: toDateTime(row.date_creation) ?? undefined,
      updatedAt: toDateTime(row.derniere_connexion) ?? undefined,
    };
  });
  if (usersToInsert.length) {
    await db.insert(user).values(usersToInsert);
  }

  djRows.forEach((row) => {
    const mappedUserId = row.user_id ? userMap.get(row.user_id) : undefined;
    if (mappedUserId) {
      djMap.set(row.id, mappedUserId);
    }
  });

  const clientsToInsert = clientRows.map((row) => {
    const id = randomUUID();
    clientMap.set(row.id, id);
    return {
      id,
      orgId,
      nom: row.nom,
      categories: row.categories || null,
      notes: row.notes || null,
      createdAt: toDateTime(row.created_at) ?? undefined,
      updatedAt: toDateTime(row.updated_at) ?? undefined,
    };
  });
  if (clientsToInsert.length) {
    await tenantDb.insert(client).values(clientsToInsert);
  }

  const contactsToInsert = contactRows
    .map((row) => {
      const clientId = clientMap.get(row.client_id);
      if (!clientId) return null;
      return {
        id: randomUUID(),
        clientId,
        nom: row.nom || "Contact",
        email: row.email || null,
        telephone: row.telephone || null,
        role: row.role || null,
        createdAt: toDateTime(row.created_at) ?? undefined,
      };
    })
    .filter(Boolean) as any[];
  if (contactsToInsert.length) {
    await tenantDb.insert(clientContact).values(contactsToInsert);
  }

  const prestationsToInsert = prestationRows.map((row) => {
    const id = randomUUID();
    prestationMap.set(row.id, id);
    const djId = row.dj_id ? djMap.get(row.dj_id) : undefined;
    const technicienId = row.technicien_id
      ? userMap.get(row.technicien_id)
      : undefined;
    const createurId = row.createur_id ? userMap.get(row.createur_id) : undefined;
    return {
      id,
      orgId,
      clientId: row.client_id ? clientMap.get(row.client_id) : null,
      clientNom: row.client,
      clientEmail: row.client_email || null,
      clientTelephone: row.client_telephone || null,
      lieu: row.lieu,
      lieuLat: row.lieu_lat ?? null,
      lieuLng: row.lieu_lng ?? null,
      dateDebut: toDate(row.date_debut),
      dateFin: toDate(row.date_fin),
      heureDebut: row.heure_debut ?? null,
      heureFin: row.heure_fin ?? null,
      statut: row.statut || "planifiee",
      notes: row.notes || null,
      createurId: createurId ?? null,
      djId: djId ?? null,
      technicienId: technicienId ?? null,
      distanceKm: row.distance_km ?? null,
      distanceSource: row.distance_source ?? null,
      indemniteKm: row.indemnite_km ?? null,
      customFields: parseJson(row.custom_fields),
      createdAt: toDateTime(row.date_creation) ?? undefined,
      updatedAt: toDateTime(row.date_modification) ?? undefined,
    };
  });
  if (prestationsToInsert.length) {
    await tenantDb.insert(prestation).values(prestationsToInsert);
  }

  const devisToInsert = devisRows.map((row) => {
    const id = randomUUID();
    devisMap.set(row.id, id);
    return {
      id,
      orgId,
      numero: row.numero,
      clientNom: row.client_nom,
      clientEmail: row.client_email || null,
      clientTelephone: row.client_telephone || null,
      clientAdresse: row.client_adresse || null,
      clientSiren: row.client_siren || null,
      clientTva: row.client_tva || null,
      clientProfessionnel: !!row.client_professionnel,
      clientId: row.client_id ? clientMap.get(row.client_id) : null,
      adresseLivraison: row.adresse_livraison || null,
      natureOperation: row.nature_operation || null,
      tvaSurDebits: !!row.tva_sur_debits,
      numeroBonCommande: row.numero_bon_commande || null,
      tvaIncluse: row.tva_incluse !== null ? !!row.tva_incluse : true,
      prestationTitre: row.prestation_titre,
      prestationDescription: row.prestation_description || null,
      datePrestation: toDate(row.date_prestation),
      heureDebut: row.heure_debut ?? null,
      heureFin: row.heure_fin ?? null,
      lieu: row.lieu,
      tarifHoraire: row.tarif_horaire ?? "0",
      dureeHeures: row.duree_heures ?? "0",
      montantHt: row.montant_ht ?? "0",
      tauxTva: row.taux_tva ?? "20",
      montantTva: row.montant_tva ?? "0",
      montantTtc: row.montant_ttc ?? "0",
      remisePourcentage: row.remise_pourcentage ?? "0",
      remiseMontant: row.remise_montant ?? "0",
      fraisTransport: row.frais_transport ?? "0",
      fraisMateriel: row.frais_materiel ?? "0",
      statut: row.statut || "brouillon",
      dateCreation: toDateTime(row.date_creation) ?? undefined,
      dateValidite: toDate(row.date_validite),
      dateEnvoi: toDateTime(row.date_envoi),
      dateAcceptation: toDateTime(row.date_acceptation),
      dateAnnulation: toDateTime(row.date_annulation),
      signatureToken: row.signature_token || null,
      signatureImage: row.signature_image || null,
      signatureDate: toDateTime(row.signature_date),
      signatureIp: row.signature_ip || null,
      estSigne: !!row.est_signe,
      contenuHtml: row.contenu_html || null,
      acompteRequis: !!row.acompte_requis,
      acomptePourcentage: row.acompte_pourcentage ?? "0",
      acompteMontant: row.acompte_montant ?? "0",
      acomptePaye: !!row.acompte_paye,
      datePaiementAcompte: toDateTime(row.date_paiement_acompte),
      stripePaymentIntentId: row.stripe_payment_intent_id || null,
      stripePaymentLink: row.stripe_payment_link || null,
      paymentToken: row.payment_token || null,
      djId: row.dj_id ? djMap.get(row.dj_id) : null,
      createurId: row.createur_id ? userMap.get(row.createur_id) : null,
      prestationId: row.prestation_id ? prestationMap.get(row.prestation_id) : null,
    };
  });
  if (devisToInsert.length) {
    await tenantDb.insert(devis).values(devisToInsert);
  }

  const facturesToInsert = factureRows.map((row) => {
    const id = randomUUID();
    factureMap.set(row.id, id);
    return {
      id,
      orgId,
      numero: row.numero,
      clientNom: row.client_nom,
      clientEmail: row.client_email || null,
      clientTelephone: row.client_telephone || null,
      clientAdresse: row.client_adresse || null,
      clientSiren: row.client_siren || null,
      clientTva: row.client_tva || null,
      clientId: row.client_id ? clientMap.get(row.client_id) : null,
      adresseLivraison: row.adresse_livraison || null,
      natureOperation: row.nature_operation || null,
      tvaSurDebits: !!row.tva_sur_debits,
      numeroBonCommande: row.numero_bon_commande || null,
      clientProfessionnel: !!row.client_professionnel,
      prestationTitre: row.prestation_titre,
      prestationDescription: row.prestation_description || null,
      datePrestation: toDate(row.date_prestation),
      heureDebut: row.heure_debut ?? null,
      heureFin: row.heure_fin ?? null,
      lieu: row.lieu,
      tarifHoraire: row.tarif_horaire ?? "0",
      dureeHeures: row.duree_heures ?? "0",
      montantHt: row.montant_ht ?? "0",
      tauxTva: row.taux_tva ?? "20",
      montantTva: row.montant_tva ?? "0",
      montantTtc: row.montant_ttc ?? "0",
      montantPaye: row.montant_paye ?? "0",
      remisePourcentage: row.remise_pourcentage ?? "0",
      remiseMontant: row.remise_montant ?? "0",
      fraisTransport: row.frais_transport ?? "0",
      fraisMateriel: row.frais_materiel ?? "0",
      statut: row.statut || "brouillon",
      dateCreation: toDateTime(row.date_creation) ?? undefined,
      dateEcheance: toDate(row.date_echeance),
      datePaiement: toDate(row.date_paiement),
      dateEnvoi: toDateTime(row.date_envoi),
      dateAnnulation: toDateTime(row.date_annulation),
      modePaiement: row.mode_paiement || null,
      modePaiementSouhaite: row.mode_paiement_souhaite || null,
      referencePaiement: row.reference_paiement || null,
      conditionsPaiement: row.conditions_paiement || null,
      notes: row.notes || null,
      acompteRequis: !!row.acompte_requis,
      acomptePourcentage: row.acompte_pourcentage ?? "0",
      acompteMontant: row.acompte_montant ?? "0",
      acomptePaye: !!row.acompte_paye,
      datePaiementAcompte: toDateTime(row.date_paiement_acompte),
      stripePaymentIntentId: row.stripe_payment_intent_id || null,
      stripePaymentLink: row.stripe_payment_link || null,
      paymentToken: row.payment_token || null,
      djId: row.dj_id ? djMap.get(row.dj_id) : null,
      createurId: row.createur_id ? userMap.get(row.createur_id) : null,
      prestationId: row.prestation_id ? prestationMap.get(row.prestation_id) : null,
      devisId: row.devis_id ? devisMap.get(row.devis_id) : null,
    };
  });
  if (facturesToInsert.length) {
    await tenantDb.insert(facture).values(facturesToInsert);
  }

  const paiementsToInsert = paiementRows
    .map((row) => {
      return {
        id: randomUUID(),
        factureId: row.facture_id ? factureMap.get(row.facture_id) : null,
        devisId: row.devis_id ? devisMap.get(row.devis_id) : null,
        montant: row.montant ?? "0",
        mode: row.mode_paiement || null,
        statut: row.statut || "en_attente",
        reference: row.stripe_payment_intent_id || row.numero || null,
        justificatifPath: row.justificatif_path || null,
        commentaire: row.commentaire || null,
        createdAt: toDateTime(row.date_creation) ?? undefined,
      };
    })
    .filter((row) => row.factureId || row.devisId);
  if (paiementsToInsert.length) {
    await tenantDb.insert(paiement).values(paiementsToInsert);
  }

  const avoirsToInsert = avoirRows
    .map((row) => {
      const factureId = row.facture_id ? factureMap.get(row.facture_id) : null;
      if (!factureId) return null;
      return {
        id: randomUUID(),
        factureId,
        numero: row.numero,
        montantHt: row.montant_ht ?? "0",
        montantTva: row.montant_tva ?? "0",
        montantTtc: row.montant_ttc ?? "0",
        statut: row.statut || "brouillon",
        dateCreation: toDateTime(row.date_creation) ?? undefined,
      };
    })
    .filter(Boolean) as any[];
  if (avoirsToInsert.length) {
    await tenantDb.insert(avoir).values(avoirsToInsert);
  }

  const materielsToInsert = materielRows.map((row) => {
    const id = randomUUID();
    materielMap.set(row.id, id);
    return {
      id,
      orgId,
      nom: row.nom,
      categorie: row.categorie || null,
      quantite: row.quantite ?? 1,
      statut: row.statut || "disponible",
      prixLocation: row.prix_location ?? "0",
      numeroSerie: row.numero_serie || null,
      codeBarre: row.code_barre || null,
      notesTechnicien: row.notes_technicien || null,
    };
  });
  if (materielsToInsert.length) {
    await tenantDb.insert(materiel).values(materielsToInsert);
  }

  const materielPrestationsToInsert = materielPrestaRows
    .map((row) => {
      const materielId = materielMap.get(row.materiel_id);
      const prestationId = row.prestation_id
        ? prestationMap.get(row.prestation_id)
        : null;
      if (!materielId || !prestationId) return null;
      return {
        id: randomUUID(),
        materielId,
        prestationId,
        quantite: row.quantite ?? 1,
      };
    })
    .filter(Boolean) as any[];
  if (materielPrestationsToInsert.length) {
    await tenantDb.insert(materielPrestation).values(materielPrestationsToInsert);
  }

  const mouvementsToInsert = mouvementRows
    .map((row) => {
      const materielId = materielMap.get(row.materiel_id);
      if (!materielId) return null;
      return {
        id: randomUUID(),
        materielId,
        prestationId: row.prestation_id
          ? prestationMap.get(row.prestation_id)
          : null,
        typeMouvement: row.type_mouvement,
        quantite: row.quantite ?? 1,
        numeroSerie: row.numero_serie || null,
        codeBarre: row.code_barre || null,
        createdAt: toDateTime(row.date_mouvement) ?? undefined,
      };
    })
    .filter(Boolean) as any[];
  if (mouvementsToInsert.length) {
    await tenantDb.insert(mouvementMateriel).values(mouvementsToInsert);
  }

  const params = paramRows[0];
  if (params) {
  await tenantDb.insert(parametresEntreprise).values({
      id: randomUUID(),
      orgId,
      nomEntreprise: params.nom_entreprise || "Planify",
      slogan: params.slogan || null,
      adresse: params.adresse || null,
      codePostal: params.code_postal || null,
      ville: params.ville || null,
      telephone: params.telephone || null,
      email: params.email || null,
      emailSignature: params.email_signature || null,
      siteWeb: params.site_web || null,
      siret: params.siret || null,
      tvaIntracommunautaire: params.tva_intracommunautaire || null,
      formeJuridique: params.forme_juridique || null,
      capitalSocial: params.capital_social || null,
      rcsVille: params.rcs_ville || null,
      numeroRcs: params.numero_rcs || null,
      penalitesRetard: params.penalites_retard || null,
      escompte: params.escompte || null,
      indemniteRecouvrement: params.indemnite_recouvrement ?? "40",
      tvaNonApplicable: !!params.tva_non_applicable,
      tauxTvaDefaut: params.taux_tva_defaut ?? "20",
      devise: params.devise || "EUR",
      langue: params.langue || "fr",
      logoPath: params.logo_path || null,
      signatureEntreprisePath: params.signature_entreprise_path || null,
      stripeEnabled: !!params.stripe_enabled,
      stripePublicKey: params.stripe_public_key || null,
      stripeSecretKey: params.stripe_secret_key || null,
      ribIban: params.rib_iban || null,
      ribBic: params.rib_bic || null,
      ribTitulaire: params.rib_titulaire || null,
      ribBanque: params.rib_banque || null,
      uiTheme: params.ui_theme || "classic",
      uiDensity: params.ui_density || "comfortable",
      uiFont: params.ui_font || null,
      uiRadius: params.ui_radius ?? 14,
      uiCustomCss: params.ui_custom_css || null,
      showAiMenu: params.show_ai_menu ?? true,
      showAiInsights: params.show_ai_insights ?? true,
      showQuickActions: params.show_quick_actions ?? true,
      showRecentMissions: params.show_recent_missions ?? true,
      showStatsCards: params.show_stats_cards ?? true,
    });
  }

  const sequencesToInsert = sequenceRows.map((row) => ({
    id: randomUUID(),
    orgId,
    type: row.prefix,
    prefix: row.prefix,
    currentNumber: row.last_number ?? 0,
    updatedAt: new Date(),
  }));
  if (sequencesToInsert.length) {
    await tenantDb.insert(documentSequence).values(sequencesToInsert);
  }

  const ratingsToInsert = ratingRows
    .map((row) => {
      const prestationId = prestationMap.get(row.prestation_id);
      if (!prestationId) return null;
      const note = row.rating_dj ?? row.rating_technicien ?? null;
      if (!note) return null;
      return {
        id: randomUUID(),
        prestationId,
        note,
        commentaire: row.commentaire || null,
        token: row.token || null,
        createdAt: toDateTime(row.created_at) ?? undefined,
      };
    })
    .filter(Boolean) as any[];
  if (ratingsToInsert.length) {
    await tenantDb.insert(prestationRating).values(ratingsToInsert);
  }

  console.log("Migration terminee");
}

main().finally(() => sqlite.close());

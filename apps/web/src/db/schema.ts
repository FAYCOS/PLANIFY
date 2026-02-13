import {
  pgTable,
  uuid,
  text,
  varchar,
  boolean,
  timestamp,
  integer,
  numeric,
  date,
  time,
  jsonb,
  uniqueIndex,
} from "drizzle-orm/pg-core";

export const organization = pgTable("organizations", {
  id: uuid("id").defaultRandom().primaryKey(),
  name: text("name").notNull(),
  country: text("country"),
  address: text("address"),
  phone: varchar("phone", { length: 32 }),
  size: text("size"),
  sector: text("sector"),
  createdByUserId: uuid("created_by_user_id"),
  dbSchema: text("db_schema"),
  dbUrl: text("db_url"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const plan = pgTable(
  "plans",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    code: varchar("code", { length: 32 }).notNull(),
    name: text("name").notNull(),
    status: varchar("status", { length: 16 }).default("active").notNull(),
    priceCents: integer("price_cents").default(0).notNull(),
    currency: varchar("currency", { length: 8 }).default("EUR").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (table) => ({
    codeIdx: uniqueIndex("plans_code_unique").on(table.code),
  }),
);

export const orgPlan = pgTable("org_plans", {
  id: uuid("id").defaultRandom().primaryKey(),
  orgId: uuid("org_id")
    .notNull()
    .references(() => organization.id, { onDelete: "cascade" }),
  planId: uuid("plan_id")
    .notNull()
    .references(() => plan.id, { onDelete: "restrict" }),
  status: varchar("status", { length: 16 }).default("active").notNull(),
  startedAt: timestamp("started_at", { withTimezone: true }).defaultNow().notNull(),
  endsAt: timestamp("ends_at", { withTimezone: true }),
});


// Better-auth core tables
export const user = pgTable(
  "user",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    email: text("email").notNull(),
    emailVerified: boolean("email_verified").default(false).notNull(),
    name: text("name").notNull(),
    image: text("image"),
    role: varchar("role", { length: 32 }).default("member").notNull(),
    nom: text("nom"),
    prenom: text("prenom"),
    telephone: varchar("telephone", { length: 32 }),
    mustChangePassword: boolean("must_change_password").default(false).notNull(),
    orgId: uuid("org_id").references(() => organization.id),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (table) => ({
    emailIdx: uniqueIndex("user_email_unique").on(table.email),
  }),
);

export const session = pgTable(
  "session",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    userId: uuid("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
    token: text("token").notNull(),
    ipAddress: text("ip_address"),
    userAgent: text("user_agent"),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (table) => ({
    tokenIdx: uniqueIndex("session_token_unique").on(table.token),
  }),
);

export const account = pgTable(
  "account",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    providerId: text("provider_id").notNull(),
    accountId: text("account_id").notNull(),
    userId: uuid("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    accessToken: text("access_token"),
    refreshToken: text("refresh_token"),
    idToken: text("id_token"),
    accessTokenExpiresAt: timestamp("access_token_expires_at", { withTimezone: true }),
    refreshTokenExpiresAt: timestamp("refresh_token_expires_at", { withTimezone: true }),
    scope: text("scope"),
    password: text("password"),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (table) => ({
    providerAccountIdx: uniqueIndex("account_provider_unique").on(
      table.providerId,
      table.accountId,
    ),
  }),
);

export const verification = pgTable("verification", {
  id: uuid("id").defaultRandom().primaryKey(),
  identifier: text("identifier").notNull(),
  value: text("value").notNull(),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const team = pgTable("teams", {
  id: uuid("id").defaultRandom().primaryKey(),
  orgId: uuid("org_id")
    .notNull()
    .references(() => organization.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  description: text("description"),
  createdByUserId: uuid("created_by_user_id").references(() => user.id, {
    onDelete: "set null",
  }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const teamMember = pgTable(
  "team_members",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    teamId: uuid("team_id")
      .notNull()
      .references(() => team.id, { onDelete: "cascade" }),
    userId: uuid("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    role: varchar("role", { length: 32 }).default("member").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (table) => ({
    uniqueMember: uniqueIndex("team_member_unique").on(table.teamId, table.userId),
  }),
);

export const invitation = pgTable(
  "invitations",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    orgId: uuid("org_id")
      .notNull()
      .references(() => organization.id, { onDelete: "cascade" }),
    email: text("email").notNull(),
    role: varchar("role", { length: 32 }).default("member").notNull(),
    teamId: uuid("team_id").references(() => team.id, { onDelete: "set null" }),
    tokenHash: text("token_hash").notNull(),
    status: varchar("status", { length: 16 }).default("pending").notNull(),
    expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
    createdByUserId: uuid("created_by_user_id").references(() => user.id, {
      onDelete: "set null",
    }),
    acceptedByUserId: uuid("accepted_by_user_id").references(() => user.id, {
      onDelete: "set null",
    }),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    acceptedAt: timestamp("accepted_at", { withTimezone: true }),
  },
  (table) => ({
    tokenIdx: uniqueIndex("invitations_token_unique").on(table.tokenHash),
  }),
);

export const signupFlow = pgTable("signup_flows", {
  id: uuid("id").defaultRandom().primaryKey(),
  email: text("email").notNull(),
  userId: uuid("user_id").references(() => user.id, { onDelete: "set null" }),
  orgId: uuid("org_id").references(() => organization.id, {
    onDelete: "set null",
  }),
  invitationId: uuid("invitation_id").references(() => invitation.id, {
    onDelete: "set null",
  }),
  companyName: text("company_name"),
  country: text("country"),
  address: text("address"),
  phone: varchar("phone", { length: 32 }),
  size: text("size"),
  sector: text("sector"),
  status: varchar("status", { length: 32 }).default("draft").notNull(),
  codeHash: text("code_hash"),
  codeExpiresAt: timestamp("code_expires_at", { withTimezone: true }),
  attemptsCount: integer("attempts_count").default(0).notNull(),
  lastSentAt: timestamp("last_sent_at", { withTimezone: true }),
  resendAvailableAt: timestamp("resend_available_at", { withTimezone: true }),
  planId: uuid("plan_id").references(() => plan.id, { onDelete: "set null" }),
  provisioningStatus: varchar("provisioning_status", { length: 32 }).default(
    "pending",
  ),
  dbSchema: text("db_schema"),
  dbUrl: text("db_url"),
  lastError: text("last_error"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const auditLog = pgTable("audit_logs", {
  id: uuid("id").defaultRandom().primaryKey(),
  orgId: uuid("org_id").references(() => organization.id),
  userId: uuid("user_id").references(() => user.id, { onDelete: "set null" }),
  action: varchar("action", { length: 64 }).notNull(),
  entityType: varchar("entity_type", { length: 64 }).notNull(),
  entityId: uuid("entity_id"),
  ipAddress: text("ip_address"),
  userAgent: text("user_agent"),
  metadata: jsonb("metadata"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const stripeEvent = pgTable(
  "stripe_events",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    eventId: text("event_id").notNull(),
    type: text("type").notNull(),
    payload: jsonb("payload"),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (table) => ({
    eventIdx: uniqueIndex("stripe_events_event_unique").on(table.eventId),
  }),
);

export const client = pgTable("clients", {
  id: uuid("id").defaultRandom().primaryKey(),
  orgId: uuid("org_id").references(() => organization.id),
  nom: text("nom").notNull(),
  prenom: text("prenom"),
  email: text("email"),
  telephone: varchar("telephone", { length: 32 }),
  adresseFacturation: text("adresse_facturation"),
  categories: text("categories"),
  notes: text("notes"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const clientContact = pgTable("client_contacts", {
  id: uuid("id").defaultRandom().primaryKey(),
  clientId: uuid("client_id")
    .notNull()
    .references(() => client.id, { onDelete: "cascade" }),
  nom: text("nom").notNull(),
  email: text("email"),
  telephone: varchar("telephone", { length: 32 }),
  role: text("role"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const prestation = pgTable("prestations", {
  id: uuid("id").defaultRandom().primaryKey(),
  orgId: uuid("org_id").references(() => organization.id),
  clientId: uuid("client_id").references(() => client.id),
  clientNom: text("client_nom").notNull(),
  clientEmail: text("client_email"),
  clientTelephone: varchar("client_telephone", { length: 32 }),
  lieu: text("lieu"),
  lieuLat: numeric("lieu_lat", { precision: 10, scale: 6 }),
  lieuLng: numeric("lieu_lng", { precision: 10, scale: 6 }),
  dateDebut: date("date_debut"),
  dateFin: date("date_fin"),
  heureDebut: time("heure_debut"),
  heureFin: time("heure_fin"),
  statut: varchar("statut", { length: 32 }).default("planifiee"),
  notes: text("notes"),
  createurId: uuid("createur_id").references(() => user.id),
  djId: uuid("dj_id").references(() => user.id),
  technicienId: uuid("technicien_id").references(() => user.id),
  distanceKm: numeric("distance_km", { precision: 10, scale: 2 }),
  distanceSource: text("distance_source"),
  indemniteKm: numeric("indemnite_km", { precision: 10, scale: 2 }),
  customFields: jsonb("custom_fields"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const devis = pgTable(
  "devis",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    orgId: uuid("org_id").references(() => organization.id),
    numero: varchar("numero", { length: 64 }).notNull(),
    clientNom: text("client_nom").notNull(),
    clientEmail: text("client_email"),
    clientTelephone: varchar("client_telephone", { length: 32 }),
    clientAdresse: text("client_adresse"),
    clientSiren: varchar("client_siren", { length: 32 }),
    clientTva: varchar("client_tva", { length: 32 }),
    clientProfessionnel: boolean("client_professionnel").default(false),
    clientId: uuid("client_id").references(() => client.id),
    adresseLivraison: text("adresse_livraison"),
    natureOperation: text("nature_operation"),
    tvaSurDebits: boolean("tva_sur_debits").default(false),
    numeroBonCommande: text("numero_bon_commande"),
    tvaIncluse: boolean("tva_incluse").default(true),
    prestationTitre: text("prestation_titre").notNull(),
    prestationDescription: text("prestation_description"),
    datePrestation: date("date_prestation"),
    heureDebut: time("heure_debut"),
    heureFin: time("heure_fin"),
    lieu: text("lieu"),
    tarifHoraire: numeric("tarif_horaire", { precision: 10, scale: 2 }).default("0"),
    dureeHeures: numeric("duree_heures", { precision: 10, scale: 2 }).default("0"),
    montantHt: numeric("montant_ht", { precision: 12, scale: 2 }).default("0"),
    tauxTva: numeric("taux_tva", { precision: 5, scale: 2 }).default("20"),
    montantTva: numeric("montant_tva", { precision: 12, scale: 2 }).default("0"),
    montantTtc: numeric("montant_ttc", { precision: 12, scale: 2 }).default("0"),
    remisePourcentage: numeric("remise_pourcentage", { precision: 5, scale: 2 }).default("0"),
    remiseMontant: numeric("remise_montant", { precision: 12, scale: 2 }).default("0"),
    fraisTransport: numeric("frais_transport", { precision: 12, scale: 2 }).default("0"),
    fraisMateriel: numeric("frais_materiel", { precision: 12, scale: 2 }).default("0"),
    statut: varchar("statut", { length: 32 }).default("brouillon"),
    dateCreation: timestamp("date_creation", { withTimezone: true }).defaultNow().notNull(),
    dateValidite: date("date_validite"),
    dateEnvoi: timestamp("date_envoi", { withTimezone: true }),
    dateAcceptation: timestamp("date_acceptation", { withTimezone: true }),
    dateAnnulation: timestamp("date_annulation", { withTimezone: true }),
    signatureToken: varchar("signature_token", { length: 128 }),
    signatureImage: text("signature_image"),
    signatureDate: timestamp("signature_date", { withTimezone: true }),
    signatureIp: text("signature_ip"),
    estSigne: boolean("est_signe").default(false),
    contenuHtml: text("contenu_html"),
    acompteRequis: boolean("acompte_requis").default(false),
    acomptePourcentage: numeric("acompte_pourcentage", { precision: 5, scale: 2 }).default("0"),
    acompteMontant: numeric("acompte_montant", { precision: 12, scale: 2 }).default("0"),
    acomptePaye: boolean("acompte_paye").default(false),
    datePaiementAcompte: timestamp("date_paiement_acompte", { withTimezone: true }),
    stripePaymentIntentId: text("stripe_payment_intent_id"),
    stripePaymentLink: text("stripe_payment_link"),
    paymentToken: varchar("payment_token", { length: 128 }),
    djId: uuid("dj_id").references(() => user.id),
    createurId: uuid("createur_id").references(() => user.id),
    prestationId: uuid("prestation_id").references(() => prestation.id),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (table) => ({
    numeroIdx: uniqueIndex("devis_numero_unique").on(table.numero),
    paymentIdx: uniqueIndex("devis_payment_token_unique").on(table.paymentToken),
  }),
);

export const facture = pgTable(
  "factures",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    orgId: uuid("org_id").references(() => organization.id),
    numero: varchar("numero", { length: 64 }).notNull(),
    clientNom: text("client_nom").notNull(),
    clientEmail: text("client_email"),
    clientTelephone: varchar("client_telephone", { length: 32 }),
    clientAdresse: text("client_adresse"),
    clientSiren: varchar("client_siren", { length: 32 }),
    clientTva: varchar("client_tva", { length: 32 }),
    clientId: uuid("client_id").references(() => client.id),
    adresseLivraison: text("adresse_livraison"),
    natureOperation: text("nature_operation"),
    tvaSurDebits: boolean("tva_sur_debits").default(false),
    numeroBonCommande: text("numero_bon_commande"),
    clientProfessionnel: boolean("client_professionnel").default(false),
    prestationTitre: text("prestation_titre").notNull(),
    prestationDescription: text("prestation_description"),
    datePrestation: date("date_prestation"),
    heureDebut: time("heure_debut"),
    heureFin: time("heure_fin"),
    lieu: text("lieu"),
    tarifHoraire: numeric("tarif_horaire", { precision: 10, scale: 2 }).default("0"),
    dureeHeures: numeric("duree_heures", { precision: 10, scale: 2 }).default("0"),
    montantHt: numeric("montant_ht", { precision: 12, scale: 2 }).default("0"),
    tauxTva: numeric("taux_tva", { precision: 5, scale: 2 }).default("20"),
    montantTva: numeric("montant_tva", { precision: 12, scale: 2 }).default("0"),
    montantTtc: numeric("montant_ttc", { precision: 12, scale: 2 }).default("0"),
    montantPaye: numeric("montant_paye", { precision: 12, scale: 2 }).default("0"),
    remisePourcentage: numeric("remise_pourcentage", { precision: 5, scale: 2 }).default("0"),
    remiseMontant: numeric("remise_montant", { precision: 12, scale: 2 }).default("0"),
    fraisTransport: numeric("frais_transport", { precision: 12, scale: 2 }).default("0"),
    fraisMateriel: numeric("frais_materiel", { precision: 12, scale: 2 }).default("0"),
    statut: varchar("statut", { length: 32 }).default("brouillon"),
    dateCreation: timestamp("date_creation", { withTimezone: true }).defaultNow().notNull(),
    dateEcheance: date("date_echeance"),
    datePaiement: date("date_paiement"),
    dateEnvoi: timestamp("date_envoi", { withTimezone: true }),
    dateAnnulation: timestamp("date_annulation", { withTimezone: true }),
    modePaiement: varchar("mode_paiement", { length: 32 }),
    modePaiementSouhaite: varchar("mode_paiement_souhaite", { length: 32 }),
    referencePaiement: text("reference_paiement"),
    conditionsPaiement: text("conditions_paiement"),
    notes: text("notes"),
    acompteRequis: boolean("acompte_requis").default(false),
    acomptePourcentage: numeric("acompte_pourcentage", { precision: 5, scale: 2 }).default("0"),
    acompteMontant: numeric("acompte_montant", { precision: 12, scale: 2 }).default("0"),
    acomptePaye: boolean("acompte_paye").default(false),
    datePaiementAcompte: timestamp("date_paiement_acompte", { withTimezone: true }),
    stripePaymentIntentId: text("stripe_payment_intent_id"),
    stripePaymentLink: text("stripe_payment_link"),
    paymentToken: varchar("payment_token", { length: 128 }),
    djId: uuid("dj_id").references(() => user.id),
    createurId: uuid("createur_id").references(() => user.id),
    prestationId: uuid("prestation_id").references(() => prestation.id),
    devisId: uuid("devis_id").references(() => devis.id),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (table) => ({
    numeroIdx: uniqueIndex("facture_numero_unique").on(table.numero),
    paymentIdx: uniqueIndex("facture_payment_token_unique").on(table.paymentToken),
  }),
);

export const paiement = pgTable("paiements", {
  id: uuid("id").defaultRandom().primaryKey(),
  orgId: uuid("org_id").references(() => organization.id),
  factureId: uuid("facture_id").references(() => facture.id, { onDelete: "cascade" }),
  devisId: uuid("devis_id").references(() => devis.id, { onDelete: "cascade" }),
  montant: numeric("montant", { precision: 12, scale: 2 }).default("0"),
  mode: varchar("mode", { length: 32 }),
  statut: varchar("statut", { length: 32 }).default("en_attente"),
  reference: text("reference"),
  justificatifPath: text("justificatif_path"),
  commentaire: text("commentaire"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const avoir = pgTable("avoirs", {
  id: uuid("id").defaultRandom().primaryKey(),
  factureId: uuid("facture_id")
    .notNull()
    .references(() => facture.id, { onDelete: "cascade" }),
  numero: varchar("numero", { length: 64 }).notNull(),
  montantHt: numeric("montant_ht", { precision: 12, scale: 2 }).default("0"),
  montantTva: numeric("montant_tva", { precision: 12, scale: 2 }).default("0"),
  montantTtc: numeric("montant_ttc", { precision: 12, scale: 2 }).default("0"),
  statut: varchar("statut", { length: 32 }).default("brouillon"),
  dateCreation: timestamp("date_creation", { withTimezone: true }).defaultNow().notNull(),
});

export const materiel = pgTable("materiels", {
  id: uuid("id").defaultRandom().primaryKey(),
  orgId: uuid("org_id").references(() => organization.id),
  nom: text("nom").notNull(),
  categorie: text("categorie"),
  quantite: integer("quantite").default(1).notNull(),
  statut: varchar("statut", { length: 32 }).default("disponible"),
  prixLocation: numeric("prix_location", { precision: 12, scale: 2 }).default("0"),
  numeroSerie: varchar("numero_serie", { length: 128 }),
  codeBarre: varchar("code_barre", { length: 128 }),
  notesTechnicien: text("notes_technicien"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const materielPrestation = pgTable("materiels_prestations", {
  id: uuid("id").defaultRandom().primaryKey(),
  materielId: uuid("materiel_id")
    .notNull()
    .references(() => materiel.id, { onDelete: "cascade" }),
  prestationId: uuid("prestation_id")
    .notNull()
    .references(() => prestation.id, { onDelete: "cascade" }),
  quantite: integer("quantite").default(1).notNull(),
});

export const mouvementMateriel = pgTable("mouvements_materiel", {
  id: uuid("id").defaultRandom().primaryKey(),
  materielId: uuid("materiel_id")
    .notNull()
    .references(() => materiel.id, { onDelete: "cascade" }),
  prestationId: uuid("prestation_id").references(() => prestation.id, {
    onDelete: "set null",
  }),
  typeMouvement: varchar("type_mouvement", { length: 16 }).notNull(),
  quantite: integer("quantite").default(1).notNull(),
  numeroSerie: varchar("numero_serie", { length: 128 }),
  codeBarre: varchar("code_barre", { length: 128 }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const parametresEntreprise = pgTable("parametres_entreprise", {
  id: uuid("id").defaultRandom().primaryKey(),
  orgId: uuid("org_id").references(() => organization.id),
  nomEntreprise: text("nom_entreprise").notNull().default("Planify"),
  slogan: text("slogan"),
  adresse: text("adresse"),
  codePostal: varchar("code_postal", { length: 16 }),
  ville: text("ville"),
  telephone: varchar("telephone", { length: 32 }),
  email: text("email"),
  emailSignature: text("email_signature"),
  siteWeb: text("site_web"),
  siret: varchar("siret", { length: 32 }),
  tvaIntracommunautaire: varchar("tva_intracommunautaire", { length: 32 }),
  formeJuridique: text("forme_juridique"),
  capitalSocial: text("capital_social"),
  rcsVille: text("rcs_ville"),
  numeroRcs: text("numero_rcs"),
  penalitesRetard: text("penalites_retard"),
  escompte: text("escompte"),
  indemniteRecouvrement: numeric("indemnite_recouvrement", {
    precision: 8,
    scale: 2,
  }).default("40"),
  tvaNonApplicable: boolean("tva_non_applicable").default(false),
  tauxTvaDefaut: numeric("taux_tva_defaut", { precision: 5, scale: 2 }).default(
    "20",
  ),
  devise: varchar("devise", { length: 8 }).default("EUR"),
  langue: varchar("langue", { length: 8 }).default("fr"),
  logoPath: text("logo_path"),
  signatureEntreprisePath: text("signature_entreprise_path"),
  stripeEnabled: boolean("stripe_enabled").default(false),
  stripePublicKey: text("stripe_public_key"),
  stripeSecretKey: text("stripe_secret_key"),
  ribIban: text("rib_iban"),
  ribBic: text("rib_bic"),
  ribTitulaire: text("rib_titulaire"),
  ribBanque: text("rib_banque"),
  uiTheme: text("ui_theme").default("classic"),
  uiDensity: text("ui_density").default("comfortable"),
  uiFont: text("ui_font"),
  uiRadius: integer("ui_radius").default(14),
  uiCustomCss: text("ui_custom_css"),
  showAiMenu: boolean("show_ai_menu").default(true),
  showAiInsights: boolean("show_ai_insights").default(true),
  showQuickActions: boolean("show_quick_actions").default(true),
  showRecentMissions: boolean("show_recent_missions").default(true),
  showStatsCards: boolean("show_stats_cards").default(true),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const documentSequence = pgTable("document_sequences", {
  id: uuid("id").defaultRandom().primaryKey(),
  orgId: uuid("org_id").references(() => organization.id),
  type: varchar("type", { length: 16 }).notNull(),
  prefix: varchar("prefix", { length: 16 }),
  currentNumber: integer("current_number").default(0).notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const prestationRating = pgTable("prestation_ratings", {
  id: uuid("id").defaultRandom().primaryKey(),
  prestationId: uuid("prestation_id")
    .notNull()
    .references(() => prestation.id, { onDelete: "cascade" }),
  note: integer("note").notNull(),
  commentaire: text("commentaire"),
  token: varchar("token", { length: 128 }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

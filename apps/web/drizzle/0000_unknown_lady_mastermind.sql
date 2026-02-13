CREATE TABLE "account" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"provider_id" text NOT NULL,
	"account_id" text NOT NULL,
	"user_id" uuid NOT NULL,
	"access_token" text,
	"refresh_token" text,
	"id_token" text,
	"access_token_expires_at" timestamp with time zone,
	"refresh_token_expires_at" timestamp with time zone,
	"scope" text,
	"password" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "audit_logs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid,
	"user_id" uuid,
	"action" varchar(64) NOT NULL,
	"entity_type" varchar(64) NOT NULL,
	"entity_id" uuid,
	"ip_address" text,
	"user_agent" text,
	"metadata" jsonb,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "avoirs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"facture_id" uuid NOT NULL,
	"numero" varchar(64) NOT NULL,
	"montant_ht" numeric(12, 2) DEFAULT '0',
	"montant_tva" numeric(12, 2) DEFAULT '0',
	"montant_ttc" numeric(12, 2) DEFAULT '0',
	"statut" varchar(32) DEFAULT 'brouillon',
	"date_creation" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "clients" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid,
	"nom" text NOT NULL,
	"prenom" text,
	"email" text,
	"telephone" varchar(32),
	"adresse_facturation" text,
	"categories" text,
	"notes" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "client_contacts" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"client_id" uuid NOT NULL,
	"nom" text NOT NULL,
	"email" text,
	"telephone" varchar(32),
	"role" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "devis" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid,
	"numero" varchar(64) NOT NULL,
	"client_nom" text NOT NULL,
	"client_email" text,
	"client_telephone" varchar(32),
	"client_adresse" text,
	"client_siren" varchar(32),
	"client_tva" varchar(32),
	"client_professionnel" boolean DEFAULT false,
	"client_id" uuid,
	"adresse_livraison" text,
	"nature_operation" text,
	"tva_sur_debits" boolean DEFAULT false,
	"numero_bon_commande" text,
	"tva_incluse" boolean DEFAULT true,
	"prestation_titre" text NOT NULL,
	"prestation_description" text,
	"date_prestation" date,
	"heure_debut" time,
	"heure_fin" time,
	"lieu" text,
	"tarif_horaire" numeric(10, 2) DEFAULT '0',
	"duree_heures" numeric(10, 2) DEFAULT '0',
	"montant_ht" numeric(12, 2) DEFAULT '0',
	"taux_tva" numeric(5, 2) DEFAULT '20',
	"montant_tva" numeric(12, 2) DEFAULT '0',
	"montant_ttc" numeric(12, 2) DEFAULT '0',
	"remise_pourcentage" numeric(5, 2) DEFAULT '0',
	"remise_montant" numeric(12, 2) DEFAULT '0',
	"frais_transport" numeric(12, 2) DEFAULT '0',
	"frais_materiel" numeric(12, 2) DEFAULT '0',
	"statut" varchar(32) DEFAULT 'brouillon',
	"date_creation" timestamp with time zone DEFAULT now() NOT NULL,
	"date_validite" date,
	"date_envoi" timestamp with time zone,
	"date_acceptation" timestamp with time zone,
	"date_annulation" timestamp with time zone,
	"signature_token" varchar(128),
	"signature_image" text,
	"signature_date" timestamp with time zone,
	"signature_ip" text,
	"est_signe" boolean DEFAULT false,
	"contenu_html" text,
	"acompte_requis" boolean DEFAULT false,
	"acompte_pourcentage" numeric(5, 2) DEFAULT '0',
	"acompte_montant" numeric(12, 2) DEFAULT '0',
	"acompte_paye" boolean DEFAULT false,
	"date_paiement_acompte" timestamp with time zone,
	"stripe_payment_intent_id" text,
	"stripe_payment_link" text,
	"payment_token" varchar(128),
	"dj_id" uuid,
	"createur_id" uuid,
	"prestation_id" uuid,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "document_sequences" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid,
	"type" varchar(16) NOT NULL,
	"prefix" varchar(16),
	"current_number" integer DEFAULT 0 NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "factures" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid,
	"numero" varchar(64) NOT NULL,
	"client_nom" text NOT NULL,
	"client_email" text,
	"client_telephone" varchar(32),
	"client_adresse" text,
	"client_siren" varchar(32),
	"client_tva" varchar(32),
	"client_id" uuid,
	"adresse_livraison" text,
	"nature_operation" text,
	"tva_sur_debits" boolean DEFAULT false,
	"numero_bon_commande" text,
	"client_professionnel" boolean DEFAULT false,
	"prestation_titre" text NOT NULL,
	"prestation_description" text,
	"date_prestation" date,
	"heure_debut" time,
	"heure_fin" time,
	"lieu" text,
	"tarif_horaire" numeric(10, 2) DEFAULT '0',
	"duree_heures" numeric(10, 2) DEFAULT '0',
	"montant_ht" numeric(12, 2) DEFAULT '0',
	"taux_tva" numeric(5, 2) DEFAULT '20',
	"montant_tva" numeric(12, 2) DEFAULT '0',
	"montant_ttc" numeric(12, 2) DEFAULT '0',
	"montant_paye" numeric(12, 2) DEFAULT '0',
	"remise_pourcentage" numeric(5, 2) DEFAULT '0',
	"remise_montant" numeric(12, 2) DEFAULT '0',
	"frais_transport" numeric(12, 2) DEFAULT '0',
	"frais_materiel" numeric(12, 2) DEFAULT '0',
	"statut" varchar(32) DEFAULT 'brouillon',
	"date_creation" timestamp with time zone DEFAULT now() NOT NULL,
	"date_echeance" date,
	"date_paiement" date,
	"date_envoi" timestamp with time zone,
	"date_annulation" timestamp with time zone,
	"mode_paiement" varchar(32),
	"mode_paiement_souhaite" varchar(32),
	"reference_paiement" text,
	"conditions_paiement" text,
	"notes" text,
	"acompte_requis" boolean DEFAULT false,
	"acompte_pourcentage" numeric(5, 2) DEFAULT '0',
	"acompte_montant" numeric(12, 2) DEFAULT '0',
	"acompte_paye" boolean DEFAULT false,
	"date_paiement_acompte" timestamp with time zone,
	"stripe_payment_intent_id" text,
	"stripe_payment_link" text,
	"payment_token" varchar(128),
	"dj_id" uuid,
	"createur_id" uuid,
	"prestation_id" uuid,
	"devis_id" uuid,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "invitations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid NOT NULL,
	"email" text NOT NULL,
	"role" varchar(32) DEFAULT 'member' NOT NULL,
	"team_id" uuid,
	"token_hash" text NOT NULL,
	"status" varchar(16) DEFAULT 'pending' NOT NULL,
	"expires_at" timestamp with time zone NOT NULL,
	"created_by_user_id" uuid,
	"accepted_by_user_id" uuid,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"accepted_at" timestamp with time zone
);
--> statement-breakpoint
CREATE TABLE "materiels" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid,
	"nom" text NOT NULL,
	"categorie" text,
	"quantite" integer DEFAULT 1 NOT NULL,
	"statut" varchar(32) DEFAULT 'disponible',
	"prix_location" numeric(12, 2) DEFAULT '0',
	"numero_serie" varchar(128),
	"code_barre" varchar(128),
	"notes_technicien" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "materiels_prestations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"materiel_id" uuid NOT NULL,
	"prestation_id" uuid NOT NULL,
	"quantite" integer DEFAULT 1 NOT NULL
);
--> statement-breakpoint
CREATE TABLE "mouvements_materiel" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"materiel_id" uuid NOT NULL,
	"prestation_id" uuid,
	"type_mouvement" varchar(16) NOT NULL,
	"quantite" integer DEFAULT 1 NOT NULL,
	"numero_serie" varchar(128),
	"code_barre" varchar(128),
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "org_plans" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid NOT NULL,
	"plan_id" uuid NOT NULL,
	"status" varchar(16) DEFAULT 'active' NOT NULL,
	"started_at" timestamp with time zone DEFAULT now() NOT NULL,
	"ends_at" timestamp with time zone
);
--> statement-breakpoint
CREATE TABLE "organizations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	"country" text,
	"address" text,
	"phone" varchar(32),
	"size" text,
	"sector" text,
	"created_by_user_id" uuid,
	"db_schema" text,
	"db_url" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "paiements" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid,
	"facture_id" uuid,
	"devis_id" uuid,
	"montant" numeric(12, 2) DEFAULT '0',
	"mode" varchar(32),
	"statut" varchar(32) DEFAULT 'en_attente',
	"reference" text,
	"justificatif_path" text,
	"commentaire" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "parametres_entreprise" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid,
	"nom_entreprise" text DEFAULT 'Planify' NOT NULL,
	"slogan" text,
	"adresse" text,
	"code_postal" varchar(16),
	"ville" text,
	"telephone" varchar(32),
	"email" text,
	"email_signature" text,
	"site_web" text,
	"siret" varchar(32),
	"tva_intracommunautaire" varchar(32),
	"forme_juridique" text,
	"capital_social" text,
	"rcs_ville" text,
	"numero_rcs" text,
	"penalites_retard" text,
	"escompte" text,
	"indemnite_recouvrement" numeric(8, 2) DEFAULT '40',
	"tva_non_applicable" boolean DEFAULT false,
	"taux_tva_defaut" numeric(5, 2) DEFAULT '20',
	"devise" varchar(8) DEFAULT 'EUR',
	"langue" varchar(8) DEFAULT 'fr',
	"logo_path" text,
	"signature_entreprise_path" text,
	"stripe_enabled" boolean DEFAULT false,
	"stripe_public_key" text,
	"stripe_secret_key" text,
	"rib_iban" text,
	"rib_bic" text,
	"rib_titulaire" text,
	"rib_banque" text,
	"ui_theme" text DEFAULT 'classic',
	"ui_density" text DEFAULT 'comfortable',
	"ui_font" text,
	"ui_radius" integer DEFAULT 14,
	"ui_custom_css" text,
	"show_ai_menu" boolean DEFAULT true,
	"show_ai_insights" boolean DEFAULT true,
	"show_quick_actions" boolean DEFAULT true,
	"show_recent_missions" boolean DEFAULT true,
	"show_stats_cards" boolean DEFAULT true,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "plans" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"code" varchar(32) NOT NULL,
	"name" text NOT NULL,
	"status" varchar(16) DEFAULT 'active' NOT NULL,
	"price_cents" integer DEFAULT 0 NOT NULL,
	"currency" varchar(8) DEFAULT 'EUR' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "prestations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid,
	"client_id" uuid,
	"client_nom" text NOT NULL,
	"client_email" text,
	"client_telephone" varchar(32),
	"lieu" text,
	"lieu_lat" numeric(10, 6),
	"lieu_lng" numeric(10, 6),
	"date_debut" date,
	"date_fin" date,
	"heure_debut" time,
	"heure_fin" time,
	"statut" varchar(32) DEFAULT 'planifiee',
	"notes" text,
	"createur_id" uuid,
	"dj_id" uuid,
	"technicien_id" uuid,
	"distance_km" numeric(10, 2),
	"distance_source" text,
	"indemnite_km" numeric(10, 2),
	"custom_fields" jsonb,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "prestation_ratings" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"prestation_id" uuid NOT NULL,
	"note" integer NOT NULL,
	"commentaire" text,
	"token" varchar(128),
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "session" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid NOT NULL,
	"expires_at" timestamp with time zone NOT NULL,
	"token" text NOT NULL,
	"ip_address" text,
	"user_agent" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "signup_flows" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"email" text NOT NULL,
	"user_id" uuid,
	"org_id" uuid,
	"invitation_id" uuid,
	"company_name" text,
	"country" text,
	"address" text,
	"phone" varchar(32),
	"size" text,
	"sector" text,
	"status" varchar(32) DEFAULT 'draft' NOT NULL,
	"code_hash" text,
	"code_expires_at" timestamp with time zone,
	"attempts_count" integer DEFAULT 0 NOT NULL,
	"last_sent_at" timestamp with time zone,
	"resend_available_at" timestamp with time zone,
	"plan_id" uuid,
	"provisioning_status" varchar(32) DEFAULT 'pending',
	"db_schema" text,
	"db_url" text,
	"last_error" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "stripe_events" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"event_id" text NOT NULL,
	"type" text NOT NULL,
	"payload" jsonb,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "teams" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid NOT NULL,
	"name" text NOT NULL,
	"description" text,
	"created_by_user_id" uuid,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "team_members" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"team_id" uuid NOT NULL,
	"user_id" uuid NOT NULL,
	"role" varchar(32) DEFAULT 'member' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "user" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"email" text NOT NULL,
	"email_verified" boolean DEFAULT false NOT NULL,
	"name" text NOT NULL,
	"image" text,
	"role" varchar(32) DEFAULT 'member' NOT NULL,
	"nom" text,
	"prenom" text,
	"telephone" varchar(32),
	"must_change_password" boolean DEFAULT false NOT NULL,
	"org_id" uuid,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "verification" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"identifier" text NOT NULL,
	"value" text NOT NULL,
	"expires_at" timestamp with time zone NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "account" ADD CONSTRAINT "account_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_logs" ADD CONSTRAINT "audit_logs_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "audit_logs" ADD CONSTRAINT "audit_logs_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "avoirs" ADD CONSTRAINT "avoirs_facture_id_factures_id_fk" FOREIGN KEY ("facture_id") REFERENCES "public"."factures"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "clients" ADD CONSTRAINT "clients_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "client_contacts" ADD CONSTRAINT "client_contacts_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "devis" ADD CONSTRAINT "devis_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "devis" ADD CONSTRAINT "devis_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "devis" ADD CONSTRAINT "devis_dj_id_user_id_fk" FOREIGN KEY ("dj_id") REFERENCES "public"."user"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "devis" ADD CONSTRAINT "devis_createur_id_user_id_fk" FOREIGN KEY ("createur_id") REFERENCES "public"."user"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "devis" ADD CONSTRAINT "devis_prestation_id_prestations_id_fk" FOREIGN KEY ("prestation_id") REFERENCES "public"."prestations"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "document_sequences" ADD CONSTRAINT "document_sequences_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "factures" ADD CONSTRAINT "factures_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "factures" ADD CONSTRAINT "factures_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "factures" ADD CONSTRAINT "factures_dj_id_user_id_fk" FOREIGN KEY ("dj_id") REFERENCES "public"."user"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "factures" ADD CONSTRAINT "factures_createur_id_user_id_fk" FOREIGN KEY ("createur_id") REFERENCES "public"."user"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "factures" ADD CONSTRAINT "factures_prestation_id_prestations_id_fk" FOREIGN KEY ("prestation_id") REFERENCES "public"."prestations"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "factures" ADD CONSTRAINT "factures_devis_id_devis_id_fk" FOREIGN KEY ("devis_id") REFERENCES "public"."devis"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "invitations" ADD CONSTRAINT "invitations_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "invitations" ADD CONSTRAINT "invitations_team_id_teams_id_fk" FOREIGN KEY ("team_id") REFERENCES "public"."teams"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "invitations" ADD CONSTRAINT "invitations_created_by_user_id_user_id_fk" FOREIGN KEY ("created_by_user_id") REFERENCES "public"."user"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "invitations" ADD CONSTRAINT "invitations_accepted_by_user_id_user_id_fk" FOREIGN KEY ("accepted_by_user_id") REFERENCES "public"."user"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "materiels" ADD CONSTRAINT "materiels_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "materiels_prestations" ADD CONSTRAINT "materiels_prestations_materiel_id_materiels_id_fk" FOREIGN KEY ("materiel_id") REFERENCES "public"."materiels"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "materiels_prestations" ADD CONSTRAINT "materiels_prestations_prestation_id_prestations_id_fk" FOREIGN KEY ("prestation_id") REFERENCES "public"."prestations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "mouvements_materiel" ADD CONSTRAINT "mouvements_materiel_materiel_id_materiels_id_fk" FOREIGN KEY ("materiel_id") REFERENCES "public"."materiels"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "mouvements_materiel" ADD CONSTRAINT "mouvements_materiel_prestation_id_prestations_id_fk" FOREIGN KEY ("prestation_id") REFERENCES "public"."prestations"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "org_plans" ADD CONSTRAINT "org_plans_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "org_plans" ADD CONSTRAINT "org_plans_plan_id_plans_id_fk" FOREIGN KEY ("plan_id") REFERENCES "public"."plans"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "paiements" ADD CONSTRAINT "paiements_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "paiements" ADD CONSTRAINT "paiements_facture_id_factures_id_fk" FOREIGN KEY ("facture_id") REFERENCES "public"."factures"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "paiements" ADD CONSTRAINT "paiements_devis_id_devis_id_fk" FOREIGN KEY ("devis_id") REFERENCES "public"."devis"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "parametres_entreprise" ADD CONSTRAINT "parametres_entreprise_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "prestations" ADD CONSTRAINT "prestations_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "prestations" ADD CONSTRAINT "prestations_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "public"."clients"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "prestations" ADD CONSTRAINT "prestations_createur_id_user_id_fk" FOREIGN KEY ("createur_id") REFERENCES "public"."user"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "prestations" ADD CONSTRAINT "prestations_dj_id_user_id_fk" FOREIGN KEY ("dj_id") REFERENCES "public"."user"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "prestations" ADD CONSTRAINT "prestations_technicien_id_user_id_fk" FOREIGN KEY ("technicien_id") REFERENCES "public"."user"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "prestation_ratings" ADD CONSTRAINT "prestation_ratings_prestation_id_prestations_id_fk" FOREIGN KEY ("prestation_id") REFERENCES "public"."prestations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "session" ADD CONSTRAINT "session_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "signup_flows" ADD CONSTRAINT "signup_flows_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "signup_flows" ADD CONSTRAINT "signup_flows_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "signup_flows" ADD CONSTRAINT "signup_flows_invitation_id_invitations_id_fk" FOREIGN KEY ("invitation_id") REFERENCES "public"."invitations"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "signup_flows" ADD CONSTRAINT "signup_flows_plan_id_plans_id_fk" FOREIGN KEY ("plan_id") REFERENCES "public"."plans"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "teams" ADD CONSTRAINT "teams_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "teams" ADD CONSTRAINT "teams_created_by_user_id_user_id_fk" FOREIGN KEY ("created_by_user_id") REFERENCES "public"."user"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "team_members" ADD CONSTRAINT "team_members_team_id_teams_id_fk" FOREIGN KEY ("team_id") REFERENCES "public"."teams"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "team_members" ADD CONSTRAINT "team_members_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "user" ADD CONSTRAINT "user_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
CREATE UNIQUE INDEX "account_provider_unique" ON "account" USING btree ("provider_id","account_id");--> statement-breakpoint
CREATE UNIQUE INDEX "devis_numero_unique" ON "devis" USING btree ("numero");--> statement-breakpoint
CREATE UNIQUE INDEX "devis_payment_token_unique" ON "devis" USING btree ("payment_token");--> statement-breakpoint
CREATE UNIQUE INDEX "facture_numero_unique" ON "factures" USING btree ("numero");--> statement-breakpoint
CREATE UNIQUE INDEX "facture_payment_token_unique" ON "factures" USING btree ("payment_token");--> statement-breakpoint
CREATE UNIQUE INDEX "invitations_token_unique" ON "invitations" USING btree ("token_hash");--> statement-breakpoint
CREATE UNIQUE INDEX "plans_code_unique" ON "plans" USING btree ("code");--> statement-breakpoint
CREATE UNIQUE INDEX "session_token_unique" ON "session" USING btree ("token");--> statement-breakpoint
CREATE UNIQUE INDEX "stripe_events_event_unique" ON "stripe_events" USING btree ("event_id");--> statement-breakpoint
CREATE UNIQUE INDEX "team_member_unique" ON "team_members" USING btree ("team_id","user_id");--> statement-breakpoint
CREATE UNIQUE INDEX "user_email_unique" ON "user" USING btree ("email");
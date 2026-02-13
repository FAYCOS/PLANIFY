import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { magicLink } from "better-auth/plugins/magic-link";

import { db } from "@/db";
import { sendTransactionalEmail } from "@/lib/email";

const appUrl =
  process.env.NEXT_PUBLIC_APP_URL ||
  process.env.BETTER_AUTH_URL ||
  "http://localhost:3000";

const authSecret = process.env.BETTER_AUTH_SECRET;
if (!authSecret) {
  throw new Error("BETTER_AUTH_SECRET is not set");
}

export const auth = betterAuth({
  baseURL: appUrl,
  secret: authSecret,
  database: drizzleAdapter(db, { provider: "pg" }),
  advanced: {
    database: {
      generateId: "uuid",
    },
  },
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false,
  },
  plugins: [
    magicLink({
      sendMagicLink: async ({ email, url }) => {
        try {
          await sendTransactionalEmail({
            to: email,
            subject: "Votre lien de connexion Planify",
            html: `
              <div style="font-family:Arial,sans-serif">
                <h2>Connexion Planify</h2>
                <p>Utilisez ce lien pour vous connecter :</p>
                <p><a href="${url}">${url}</a></p>
                <p>Si vous n'etes pas a l'origine de cette demande, ignorez cet email.</p>
              </div>
            `,
          });
        } catch (error) {
          console.warn("Email provider not configured, magic link not sent.", error);
        }
      },
    }),
  ],
});

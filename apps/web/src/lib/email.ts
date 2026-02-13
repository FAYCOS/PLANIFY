import { sendGmailEmail } from "@/lib/gmail";
import { resend } from "@/lib/resend";
import { sendMailgunEmail } from "@/lib/mailgun";

type SendEmailParams = {
  to: string;
  subject: string;
  html: string;
};

const hasGmailConfig = Boolean(
  process.env.GMAIL_CLIENT_ID &&
    process.env.GMAIL_CLIENT_SECRET &&
    process.env.GMAIL_REFRESH_TOKEN &&
    process.env.GMAIL_SENDER_EMAIL,
);

const hasMailgunConfig = Boolean(
  process.env.MAILGUN_API_KEY &&
    process.env.MAILGUN_DOMAIN &&
    process.env.MAILGUN_BASE_URL,
);

export async function sendTransactionalEmail(params: SendEmailParams) {
  if (hasGmailConfig) {
    await sendGmailEmail(params);
    return;
  }

  if (resend) {
    await resend.emails.send({
      from: process.env.RESEND_FROM_EMAIL || "Planify <onboarding@resend.dev>",
      to: params.to,
      subject: params.subject,
      html: params.html,
    });
    return;
  }

  if (hasMailgunConfig) {
    await sendMailgunEmail(params);
    return;
  }

  throw new Error("Aucun fournisseur email configure.");
}

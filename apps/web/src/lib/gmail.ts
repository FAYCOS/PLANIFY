import { google } from "googleapis";

type SendEmailParams = {
  to: string;
  subject: string;
  html: string;
};

const clientId = process.env.GMAIL_CLIENT_ID;
const clientSecret = process.env.GMAIL_CLIENT_SECRET;
const refreshToken = process.env.GMAIL_REFRESH_TOKEN;
const senderEmail = process.env.GMAIL_SENDER_EMAIL;

function ensureGmailConfig() {
  if (!clientId || !clientSecret || !refreshToken || !senderEmail) {
    throw new Error("Gmail API credentials are not configured.");
  }
}

function buildRawMessage({ to, subject, html }: SendEmailParams) {
  const message = [
    `From: ${senderEmail}`,
    `To: ${to}`,
    "MIME-Version: 1.0",
    "Content-Type: text/html; charset=utf-8",
    `Subject: ${subject}`,
    "",
    html,
  ].join("\n");

  return Buffer.from(message)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

export async function sendGmailEmail(params: SendEmailParams) {
  ensureGmailConfig();

  const oauth2Client = new google.auth.OAuth2(clientId, clientSecret);
  oauth2Client.setCredentials({ refresh_token: refreshToken });

  const gmail = google.gmail({ version: "v1", auth: oauth2Client });
  const raw = buildRawMessage(params);

  await gmail.users.messages.send({
    userId: "me",
    requestBody: { raw },
  });
}

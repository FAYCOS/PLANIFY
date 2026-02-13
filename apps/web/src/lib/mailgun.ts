type SendEmailParams = {
  to: string;
  subject: string;
  html: string;
};

const mailgunApiKey = process.env.MAILGUN_API_KEY;
const mailgunDomain = process.env.MAILGUN_DOMAIN;
const mailgunBaseUrl = process.env.MAILGUN_BASE_URL || "https://api.mailgun.net";
const mailgunSender =
  process.env.MAILGUN_SENDER_EMAIL && process.env.MAILGUN_SENDER_EMAIL.trim()
    ? process.env.MAILGUN_SENDER_EMAIL.trim()
    : mailgunDomain
      ? `Planify <postmaster@${mailgunDomain}>`
      : "Planify <postmaster@localhost>";

function ensureMailgunConfig() {
  if (!mailgunApiKey || !mailgunDomain) {
    throw new Error("Mailgun API key or domain not configured.");
  }
}

export async function sendMailgunEmail(params: SendEmailParams) {
  ensureMailgunConfig();

  const url = `${mailgunBaseUrl}/v3/${mailgunDomain}/messages`;
  const body = new URLSearchParams();
  body.append("from", mailgunSender);
  body.append("to", params.to);
  body.append("subject", params.subject);
  body.append("html", params.html);

  const auth = Buffer.from(`api:${mailgunApiKey}`).toString("base64");
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Basic ${auth}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body.toString(),
  });

  if (!response.ok) {
    const details = await response.text().catch(() => "");
    throw new Error(
      `Mailgun error (${response.status}): ${details || response.statusText}`,
    );
  }
}

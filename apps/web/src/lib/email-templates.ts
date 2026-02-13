type EmailTemplateParams = {
  appUrl: string;
  recipientName?: string | null;
  numero: string;
  link: string;
  totalTtc?: string | null;
  signLink?: string | null;
};

function wrapTemplate(title: string, body: string) {
  return `
    <div style="font-family:Arial,sans-serif;line-height:1.5;color:#111827;">
      <h2 style="margin:0 0 12px;">${title}</h2>
      ${body}
      <p style="margin-top:24px;color:#6B7280;font-size:12px;">Planify</p>
    </div>
  `;
}

export function devisSentTemplate(params: EmailTemplateParams) {
  const name = params.recipientName ? ` ${params.recipientName}` : "";
  const sign =
    params.signLink
      ? `<p><a href="${params.signLink}">Signer le devis</a></p>`
      : "";
  const body = `
    <p>Bonjour${name},</p>
    <p>Votre devis <strong>${params.numero}</strong> est disponible.</p>
    <p><a href="${params.link}">Consulter le devis (PDF)</a></p>
    ${sign}
  `;
  return wrapTemplate("Votre devis Planify", body);
}

export function devisReminderTemplate(params: EmailTemplateParams) {
  const name = params.recipientName ? ` ${params.recipientName}` : "";
  const sign =
    params.signLink
      ? `<p><a href="${params.signLink}">Signer le devis</a></p>`
      : "";
  const body = `
    <p>Bonjour${name},</p>
    <p>Petit rappel concernant votre devis <strong>${params.numero}</strong>.</p>
    <p><a href="${params.link}">Consulter le devis (PDF)</a></p>
    ${sign}
  `;
  return wrapTemplate("Rappel devis Planify", body);
}

export function factureSentTemplate(params: EmailTemplateParams) {
  const name = params.recipientName ? ` ${params.recipientName}` : "";
  const total = params.totalTtc ? ` Montant TTC : ${params.totalTtc} €.` : "";
  const body = `
    <p>Bonjour${name},</p>
    <p>Votre facture <strong>${params.numero}</strong> est disponible.${total}</p>
    <p><a href="${params.link}">Consulter la facture (PDF)</a></p>
  `;
  return wrapTemplate("Votre facture Planify", body);
}

export function factureReminderTemplate(params: EmailTemplateParams) {
  const name = params.recipientName ? ` ${params.recipientName}` : "";
  const total = params.totalTtc ? ` Montant TTC : ${params.totalTtc} €.` : "";
  const body = `
    <p>Bonjour${name},</p>
    <p>Petit rappel concernant la facture <strong>${params.numero}</strong>.${total}</p>
    <p><a href="${params.link}">Consulter la facture (PDF)</a></p>
  `;
  return wrapTemplate("Rappel facture Planify", body);
}

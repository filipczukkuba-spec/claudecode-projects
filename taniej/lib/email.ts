export async function sendEmail(subject: string, html: string) {
  const key = process.env.RESEND_API_KEY;
  if (!key) return; // silently skip if not configured

  await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: "taniejkupuj <onboarding@resend.dev>",
      to: ["kubafilipczuktaniejkupuj@gmail.com"],
      subject,
      html,
    }),
  });
}

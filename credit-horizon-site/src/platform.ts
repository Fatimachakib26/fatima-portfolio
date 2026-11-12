// Capacités de la plateforme claude.ai (quand le site est publié en artefact) avec repli autonome.
//  - db + user : sauvegarde privée et durable des données de l'utilisateur
//  - sample    : Risk Advisor connecté au modèle Claude
//  - downloads : téléchargement des exports
type ClaudeHost = { use: (name: string) => Promise<any> };
const host = (): ClaudeHost | null => ((window as any).claude?.use ? (window as any).claude : null);
export const inClaude = () => !!host();

const cache = new Map<string, Promise<any>>();
export function capability(name: string): Promise<any> {
  const h = host();
  if (!h) return Promise.resolve(null);
  if (!cache.has(name)) cache.set(name, h.use(name).catch(() => null));
  return cache.get(name)!;
}

export async function saveFile(name: string, content: string, type: string): Promise<boolean> {
  const dl = await capability("downloads");
  if (dl) {
    await dl.save({ filename: name, data: new Blob([content], { type }) });
    return true;
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([content], { type }));
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  return true;
}

let doc: any = null;
let timer: any = null;
let pending: string | null = null;

/** Rattache la base locale à l'espace privé de l'utilisateur ; renvoie la copie distante si elle existe. */
export async function attachCloud(): Promise<string | null> {
  const [db, user] = await Promise.all([capability("db"), capability("user")]);
  if (!db || !user) return null;
  try {
    const id = await user.id();
    if (!id) return null;
    doc = db.collection("data/users/" + id).doc("workspace");
    const snap = await doc.get();
    const json = snap.exists ? (snap.data() as any)?.json : null;
    return typeof json === "string" && json.length ? json : null;
  } catch {
    doc = null;
    return null;
  }
}

export const cloudReady = () => !!doc;

export function queueCloudSave(json: string) {
  if (!doc) return;
  pending = json;
  clearTimeout(timer);
  timer = setTimeout(async () => {
    const body = pending;
    pending = null;
    if (!body) return;
    try {
      await doc.set({ json: body, savedAt: new Date().toISOString() });
    } catch (e) {
      console.warn("Sauvegarde distante impossible", e);
    }
  }, 900);
}

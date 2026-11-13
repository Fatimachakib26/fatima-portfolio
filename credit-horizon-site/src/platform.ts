// Intégration claude.ai : identité, stockage partagé de l'équipe, IA Claude, téléchargements.
// Hors claude.ai (fichier ouvert localement), la plateforme fonctionne en « copie locale » mono-utilisateur.
type Host = { use: (name: string) => Promise<any> };
const host = (): Host | null => ((window as any).claude?.use ? (window as any).claude : null);
export const inClaude = () => !!host();

const cache = new Map<string, Promise<any>>();
export function capability(name: string): Promise<any> {
  const h = host();
  if (!h) return Promise.resolve(null);
  if (!cache.has(name)) cache.set(name, h.use(name).catch(() => null));
  return cache.get(name)!;
}

export interface Identity {
  mode: "claude" | "local";
  id: string;
  name: string;
  isOwner: boolean;
}

/** Identité de la personne connectée à claude.ai (aucun mot de passe géré par la plateforme). */
export async function identity(): Promise<Identity> {
  const user = await capability("user");
  if (!user) return { mode: "local", id: "local", name: "Copie locale", isOwner: true };
  const me = await user.me();
  return { mode: "claude", id: me.id || "anonyme", name: me.name || "Utilisateur", isOwner: !!me.isOwner };
}

export async function profiles(ids: string[]): Promise<Record<string, { name: string }>> {
  const user = await capability("user");
  if (!user || !ids.length) return {};
  try {
    return await user.profiles(ids);
  } catch {
    return {};
  }
}

export async function searchPeople(q: string): Promise<{ id: string; name: string }[]> {
  const user = await capability("user");
  if (!user) return [];
  try {
    return (await user.search(q)).map((p: any) => ({ id: p.id, name: p.name || "Sans nom" }));
  } catch {
    return [];
  }
}

/* ---------------------------------------------------------------- stockage partagé */
let wsDoc: any = null;
let rolesDoc: any = null;
let timer: any = null;
let pending: string | null = null;
let lastWritten = "";

export async function connectStore(onWorkspace: (json: string) => void, onRoles: (roles: Record<string, string>) => void) {
  const db = await capability("db");
  if (!db) return false;
  wsDoc = db.doc("workspace/main");
  rolesDoc = db.doc("config/roles");
  wsDoc.onSnapshot(
    (snap: any) => {
      const json = snap.exists ? (snap.data() as any)?.json : null;
      if (typeof json === "string" && json && json !== lastWritten) onWorkspace(json);
    },
    () => {},
  );
  rolesDoc.onSnapshot(
    (snap: any) => onRoles((snap.exists ? (snap.data() as any)?.members : null) || {}),
    () => {},
  );
  return true;
}

export const sharedStore = () => !!wsDoc;

export function queueSave(json: string, onError: (msg: string) => void) {
  if (!wsDoc) return;
  pending = json;
  clearTimeout(timer);
  timer = setTimeout(async () => {
    const body = pending;
    pending = null;
    if (!body) return;
    try {
      lastWritten = body;
      await wsDoc.set({ json: body, savedAt: new Date().toISOString() });
    } catch (e: any) {
      onError(e?.code === "not_granted" || e?.code === "permission_denied" ? "Vos droits de partage ne permettent pas d'enregistrer : demandez un accès Contributeur." : "Enregistrement impossible pour le moment : vos dernières modifications restent sur cet appareil.");
    }
  }, 700);
}

export async function saveRoles(members: Record<string, string>) {
  if (!rolesDoc) return;
  await rolesDoc.set({ members, updatedAt: new Date().toISOString() });
}

export async function saveFile(name: string, content: string, type: string) {
  const dl = await capability("downloads");
  if (dl) return dl.save({ filename: name, data: new Blob([content], { type }) });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([content], { type }));
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

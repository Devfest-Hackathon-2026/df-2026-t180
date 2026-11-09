import type { Auth, User } from "firebase/auth";

/**
 * Admin sign-in with Firebase Authentication (email and password; accounts are added in the
 * Firebase console). Firebase is loaded only when the admin side needs it, so visitors never
 * download it.
 */
const env = import.meta.env;
const config = {
  apiKey: env.VITE_FIREBASE_API_KEY as string | undefined,
  authDomain: env.VITE_FIREBASE_AUTH_DOMAIN as string | undefined,
  projectId: env.VITE_FIREBASE_PROJECT_ID as string | undefined,
  appId: env.VITE_FIREBASE_APP_ID as string | undefined,
};

/**
 * Live mode: Firebase is configured in .env, so sign-in and the admin API are real. Otherwise the
 * admin screens run on sample data and say so.
 */
export const adminLive = Boolean(config.apiKey && config.projectId);

let authPromise: Promise<Auth> | undefined;

async function auth(): Promise<Auth> {
  authPromise ??= (async () => {
    const [{ initializeApp }, { getAuth }] = await Promise.all([
      import("firebase/app"),
      import("firebase/auth"),
    ]);
    return getAuth(initializeApp(config));
  })();
  return authPromise;
}

/** Signs in; throws if the email or password is wrong. */
export async function signIn(email: string, password: string): Promise<void> {
  const { signInWithEmailAndPassword } = await import("firebase/auth");
  await signInWithEmailAndPassword(await auth(), email, password);
}

export async function signOut(): Promise<void> {
  if (!adminLive) return;
  const { signOut: firebaseSignOut } = await import("firebase/auth");
  await firebaseSignOut(await auth());
}

/** The signed-in admin, once Firebase has restored the session (null if signed out). */
export async function currentUser(): Promise<User | null> {
  const instance = await auth();
  await instance.authStateReady();
  return instance.currentUser;
}

/** A fresh ID token for the API, or null when signed out. */
export async function idToken(): Promise<string | null> {
  const user = await currentUser();
  return user ? user.getIdToken() : null;
}

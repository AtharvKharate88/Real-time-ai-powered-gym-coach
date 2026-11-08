import { useEffect, useState } from "react";
import { getCurrentUser, loginWithGoogle, logout, type AuthUser } from "../services/api";

export default function AuthStatus() {
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    getCurrentUser().then(setUser).catch(() => setUser(null));
  }, []);

  if (!user) {
    return (
      <button type="button" className="btn-ghost auth-button" onClick={loginWithGoogle}>
        Sign in with Google
      </button>
    );
  }

  return (
    <button
      type="button"
      className="btn-ghost auth-button"
      onClick={() => logout().then(() => setUser(null))}
    >
      {user.full_name ?? user.email} · Sign out
    </button>
  );
}

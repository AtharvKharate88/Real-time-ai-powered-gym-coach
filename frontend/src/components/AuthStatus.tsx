import { loginWithGoogle, type AuthUser } from "../services/api";

interface AuthStatusProps {
  user: AuthUser | null;
  loading: boolean;
  onSignOut: () => void;
}

export default function AuthStatus({
  user,
  loading,
  onSignOut,
}: AuthStatusProps) {
  if (loading) {
    return (
      <button type="button" className="btn-ghost auth-button" disabled>
        Checking account…
      </button>
    );
  }

  if (!user) {
    return (
      <button type="button" className="btn-ghost auth-button" onClick={loginWithGoogle}>
        Sign in with Google
      </button>
    );
  }

  return (
    <button type="button" className="btn-ghost auth-button" onClick={onSignOut} aria-label={`Sign out ${user.full_name ?? user.email}`} title={user.full_name ?? user.email}>
      Sign out
    </button>
  );
}

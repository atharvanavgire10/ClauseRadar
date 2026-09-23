import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, getToken, setToken } from './api';
import type { User, Workspace } from './api';

const WORKSPACE_KEY = 'clauseradar.workspace';
const EVAL_KEY = 'clauseradar.eval';

interface AuthState {
  user: User | null;
  authLoading: boolean;
  evalMode: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  explore: () => Promise<void>;
  resetEvalWorkspace: () => Promise<string>;
  logout: () => Promise<void>;
  workspaces: Workspace[];
  workspacesLoading: boolean;
  activeWorkspace: Workspace | null;
  setActiveWorkspaceId: (id: string | null) => void;
  refreshWorkspaces: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

function storedWorkspaceId(): string | null {
  try {
    return localStorage.getItem(WORKSPACE_KEY);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspacesLoading, setWorkspacesLoading] = useState(false);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(storedWorkspaceId());
  const [evalMode, setEvalMode] = useState<boolean>(() => {
    try {
      return localStorage.getItem(EVAL_KEY) === '1';
    } catch {
      return false;
    }
  });

  const refreshWorkspaces = useCallback(async () => {
    if (!getToken()) {
      setWorkspaces([]);
      return;
    }
    setWorkspacesLoading(true);
    try {
      const page = await api.workspaces();
      setWorkspaces(page.results);
      const stored = storedWorkspaceId();
      if (!stored || !page.results.some((w) => w.id === stored)) {
        const first = page.results[0]?.id ?? null;
        setActiveWorkspaceId(first);
        try {
          if (first) localStorage.setItem(WORKSPACE_KEY, first);
          else localStorage.removeItem(WORKSPACE_KEY);
        } catch {
          /* ignore */
        }
      }
    } catch {
      setWorkspaces([]);
    } finally {
      setWorkspacesLoading(false);
    }
  }, []);

  useEffect(() => {
    (async () => {
      if (!getToken()) {
        setAuthLoading(false);
        return;
      }
      try {
        const me = await api.me();
        setUser(me);
        await refreshWorkspaces();
      } catch {
        setToken(null);
        setUser(null);
      } finally {
        setAuthLoading(false);
      }
    })();
  }, [refreshWorkspaces]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.login({ email: email.trim().toLowerCase(), password });
      setToken(res.token);
      setUser(res.user);
      setEvalMode(false);
      try {
        localStorage.removeItem(EVAL_KEY);
      } catch {
        /* ignore */
      }
      await refreshWorkspaces();
    },
    [refreshWorkspaces],
  );

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      const res = await api.register({ email: email.trim().toLowerCase(), password, display_name: displayName });
      setToken(res.token);
      setUser(res.user);
      setEvalMode(false);
      try {
        localStorage.removeItem(EVAL_KEY);
      } catch {
        /* ignore */
      }
      await refreshWorkspaces();
    },
    [refreshWorkspaces],
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      /* token may already be invalid — still clear local state */
    }
    setToken(null);
    setUser(null);
    setWorkspaces([]);
    setActiveWorkspaceId(null);
    setEvalMode(false);
    try {
      localStorage.removeItem(WORKSPACE_KEY);
      localStorage.removeItem(EVAL_KEY);
    } catch {
      /* ignore */
    }
    queryClient.clear();
  }, [queryClient]);

  const explore = useCallback(async () => {
    setToken(null);
    // Prime the CSRF cookie first: browsers carrying a session cookie need
    // the token for the session POST below (eval/info sets it; harmless otherwise).
    await api.evalInfo().catch(() => null);
    const res = await api.evalSession();
    setToken(res.token);
    setUser(res.user);
    setEvalMode(true);
    try {
      localStorage.setItem(EVAL_KEY, '1');
    } catch {
      /* ignore */
    }
    await refreshWorkspaces();
  }, [refreshWorkspaces]);

  const resetEvalWorkspace = useCallback(async () => {
    const res = await api.resetEval();
    await refreshWorkspaces();
    queryClient.clear();
    return `Evaluation workspace reset — ${res.contracts ?? 6} contracts reseeded.`;
  }, [refreshWorkspaces, queryClient]);

  const setActiveWorkspaceIdAndPersist = useCallback((id: string | null) => {
    setActiveWorkspaceId(id);
    try {
      if (id) localStorage.setItem(WORKSPACE_KEY, id);
      else localStorage.removeItem(WORKSPACE_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const activeWorkspace = useMemo(
    () => workspaces.find((w) => w.id === activeWorkspaceId) ?? workspaces[0] ?? null,
    [workspaces, activeWorkspaceId],
  );

  const value = useMemo<AuthState>(
    () => ({
      user,
      authLoading,
      evalMode,
      login,
      register,
      explore,
      resetEvalWorkspace,
      logout,
      workspaces,
      workspacesLoading,
      activeWorkspace,
      setActiveWorkspaceId: setActiveWorkspaceIdAndPersist,
      refreshWorkspaces,
    }),
    [user, authLoading, evalMode, login, register, explore, resetEvalWorkspace, logout, workspaces, workspacesLoading, activeWorkspace, setActiveWorkspaceIdAndPersist, refreshWorkspaces],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}

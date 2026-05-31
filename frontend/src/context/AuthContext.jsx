import { createContext, useContext, useState } from "react";
import { login as apiLogin, logout as apiLogout, isAuthenticated, getRole, getUsername } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    if (isAuthenticated()) {
      return { username: getUsername(), role: getRole() };
    }
    return null;
  });

  const login = async (username, password) => {
    const data = await apiLogin(username, password);
    setUser({ username: data.username, role: data.role });
    return data;
  };

  const logout = () => {
    setUser(null);
    apiLogout();
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

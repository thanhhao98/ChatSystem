import React, { createContext, useContext, useEffect, useState } from "react";
import { UserContext, getMeApi, loginApi } from "../services/client";

interface AuthContextType {
  token: string | null;
  refreshToken: string | null;
  user: UserContext | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (credential: string, pass: string, tier?: string) => Promise<boolean>;
  logout: () => void;
  updateAccessToken: (newToken: string) => void;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("sgod_access_token"));
  const [refreshToken, setRefreshToken] = useState<string | null>(() => localStorage.getItem("sgod_refresh_token"));
  const [user, setUser] = useState<UserContext | null>(() => {
    const saved = localStorage.getItem("sgod_user_context");
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Kiểm tra phiên làm việc khi người dùng mở lại trang web
  useEffect(() => {
    const verifySession = async () => {
      if (token) {
        try {
          const res = await getMeApi(token);
          if (res.success && res.user_context) {
            setUser(res.user_context);
            localStorage.setItem("sgod_user_context", JSON.stringify(res.user_context));
          } else {
            logout();
          }
        } catch {
          logout();
        }
      }
      setLoading(false);
    };

    verifySession();
  }, []);

  const login = async (credential: string, pass: string, tier?: string): Promise<boolean> => {
    setError(null);
    try {
      const res = await loginApi(credential, pass, tier);
      if (res.success && res.access_token && res.user_context) {
        setToken(res.access_token);
        setUser(res.user_context);
        localStorage.setItem("sgod_access_token", res.access_token);
        localStorage.setItem("sgod_user_context", JSON.stringify(res.user_context));

        if (res.refresh_token) {
          setRefreshToken(res.refresh_token);
          localStorage.setItem("sgod_refresh_token", res.refresh_token);
        }
        return true;
      }
      setError(res.message || "Đăng nhập không thành công.");
      return false;
    } catch (err: any) {
      setError(err.message || "Lỗi kết nối tới máy chủ.");
      return false;
    }
  };

  const logout = () => {
    setToken(null);
    setRefreshToken(null);
    setUser(null);
    localStorage.removeItem("sgod_access_token");
    localStorage.removeItem("sgod_refresh_token");
    localStorage.removeItem("sgod_user_context");
  };

  const updateAccessToken = (newToken: string) => {
    setToken(newToken);
    localStorage.setItem("sgod_access_token", newToken);
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        refreshToken,
        user,
        isAuthenticated: !!token && !!user,
        loading,
        login,
        logout,
        updateAccessToken,
        error,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth phải được sử dụng bên trong AuthProvider");
  }
  return context;
};

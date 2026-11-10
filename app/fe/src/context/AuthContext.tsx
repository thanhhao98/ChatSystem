import React, { createContext, useContext, useEffect, useState } from "react";
import { UserContext, getMeApi, loginApi, refreshApi } from "../services/client";

interface AuthContextType {
  token: string | null;
  refreshToken: string | null;
  user: UserContext | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (credential: string, pass: string, tier?: string) => Promise<boolean>;
  logout: () => void;
  updateAccessToken: (newToken: string, newRefresh?: string) => void;
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

  const logout = () => {
    setToken(null);
    setRefreshToken(null);
    setUser(null);
    localStorage.removeItem("sgod_access_token");
    localStorage.removeItem("sgod_refresh_token");
    localStorage.removeItem("sgod_user_context");
  };

  const updateAccessToken = (newToken: string, newRefresh?: string) => {
    setToken(newToken);
    localStorage.setItem("sgod_access_token", newToken);
    if (newRefresh) {
      setRefreshToken(newRefresh);
      localStorage.setItem("sgod_refresh_token", newRefresh);
    }
  };

  // Đồng bộ sự kiện tự động refresh token hoặc logout từ client service
  useEffect(() => {
    const handleRefreshed = (e: any) => {
      if (e.detail?.accessToken) {
        setToken(e.detail.accessToken);
      }
      if (e.detail?.refreshToken) {
        setRefreshToken(e.detail.refreshToken);
      }
    };

    const handleLogout = () => {
      logout();
    };

    window.addEventListener("sgod:token_refreshed", handleRefreshed);
    window.addEventListener("sgod:logout", handleLogout);
    return () => {
      window.removeEventListener("sgod:token_refreshed", handleRefreshed);
      window.removeEventListener("sgod:logout", handleLogout);
    };
  }, []);

  // Kiểm tra phiên làm việc khi người dùng mở lại trang web, tự động refresh nếu hết hạn
  useEffect(() => {
    const verifySession = async () => {
      const curToken = token || localStorage.getItem("sgod_access_token");
      const curRefresh = refreshToken || localStorage.getItem("sgod_refresh_token");

      if (curToken) {
        try {
          const res = await getMeApi(curToken);
          if (res.success && res.user_context) {
            setUser(res.user_context);
            localStorage.setItem("sgod_user_context", JSON.stringify(res.user_context));
            setLoading(false);
            return;
          }
        } catch {
          // Token có thể đã hết hạn, thử refresh bằng refresh_token
          if (curRefresh) {
            try {
              const refRes = await refreshApi(curRefresh);
              if (refRes.success && refRes.access_token) {
                updateAccessToken(refRes.access_token, refRes.refresh_token);
                const meRes = await getMeApi(refRes.access_token);
                if (meRes.success && meRes.user_context) {
                  setUser(meRes.user_context);
                  localStorage.setItem("sgod_user_context", JSON.stringify(meRes.user_context));
                  setLoading(false);
                  return;
                }
              }
            } catch {
              // Refresh không thành công
            }
          }
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

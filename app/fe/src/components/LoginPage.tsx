import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";

export const LoginPage: React.FC = () => {
  const { login, error } = useAuth();
  const [credential, setCredential] = useState("");
  const [password, setPassword] = useState("");
  const [tier, setTier] = useState<string>("enterprises");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!credential || !password) return;
    setLoading(true);
    await login(credential, password, tier || undefined);
    setLoading(false);
  };

  const handleFillDemo = () => {
    setCredential("thuongpx2007@gmail.com");
    setPassword("PasswordStrong123@");
    setTier("enterprises");
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.header}>
          <div style={styles.logo}>🤖</div>
          <h2 style={styles.title}>Đăng nhập Trợ lý Chat SGOD</h2>
          <p style={styles.subtitle}>Hệ thống trợ lý AI hỗ trợ quản trị và tra cứu tài sản doanh nghiệp</p>
        </div>

        {error && <div style={styles.errorBox}>{error}</div>}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.formGroup}>
            <label style={styles.label}>Tầng truy cập (Tier):</label>
            <select
              value={tier}
              onChange={(e) => setTier(e.target.value)}
              style={styles.select}
            >
              <option value="enterprises">Quản trị viên Doanh nghiệp (Enterprise Admin)</option>
              <option value="enterprise-users">Nhân viên Doanh nghiệp (Employee)</option>
              <option value="sub-enterprises">Chi nhánh trực thuộc (Sub-Enterprise)</option>
              <option value="">Tự động nhận diện theo tài khoản</option>
            </select>
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Email hoặc Tên đăng nhập:</label>
            <input
              type="text"
              value={credential}
              onChange={(e) => setCredential(e.target.value)}
              placeholder="thuongpx2007@gmail.com"
              required
              style={styles.input}
            />
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Mật khẩu:</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              style={styles.input}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              ...styles.submitBtn,
              opacity: loading ? 0.7 : 1,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Đang xác thực với SGOD..." : "Đăng nhập ngay"}
          </button>
        </form>

        <div style={styles.footer}>
          <button type="button" onClick={handleFillDemo} style={styles.demoBtn}>
            ⚡ Điền tài khoản thử nghiệm mẫu (thuongpx2007)
          </button>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#f0f2f5",
    padding: "20px",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  },
  card: {
    width: "100%",
    maxWidth: "460px",
    backgroundColor: "#ffffff",
    borderRadius: "12px",
    boxShadow: "0 8px 24px rgba(0, 0, 0, 0.08)",
    padding: "36px",
  },
  header: {
    textAlign: "center",
    marginBottom: "24px",
  },
  logo: {
    fontSize: "44px",
    marginBottom: "8px",
  },
  title: {
    fontSize: "22px",
    fontWeight: "700",
    color: "#1a1a1a",
    margin: "0 0 6px 0",
  },
  subtitle: {
    fontSize: "13px",
    color: "#666666",
    margin: "0",
    lineHeight: "1.4",
  },
  errorBox: {
    backgroundColor: "#fee2e2",
    color: "#b91c1c",
    padding: "10px 14px",
    borderRadius: "6px",
    fontSize: "13px",
    marginBottom: "18px",
    border: "1px solid #fca5a5",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  formGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  label: {
    fontSize: "13px",
    fontWeight: "600",
    color: "#374151",
  },
  select: {
    padding: "10px 12px",
    borderRadius: "6px",
    border: "1px solid #d1d5db",
    fontSize: "14px",
    backgroundColor: "#ffffff",
    color: "#111827",
    outline: "none",
  },
  input: {
    padding: "10px 12px",
    borderRadius: "6px",
    border: "1px solid #d1d5db",
    fontSize: "14px",
    outline: "none",
    color: "#111827",
  },
  submitBtn: {
    backgroundColor: "#2563eb",
    color: "#ffffff",
    padding: "12px",
    borderRadius: "6px",
    border: "none",
    fontSize: "15px",
    fontWeight: "600",
    marginTop: "8px",
    transition: "background-color 0.2s",
  },
  footer: {
    marginTop: "20px",
    textAlign: "center",
    borderTop: "1px solid #e5e7eb",
    paddingTop: "16px",
  },
  demoBtn: {
    background: "none",
    border: "none",
    color: "#2563eb",
    fontSize: "13px",
    fontWeight: "500",
    cursor: "pointer",
    textDecoration: "underline",
  },
};

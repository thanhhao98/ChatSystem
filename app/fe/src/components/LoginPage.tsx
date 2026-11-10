import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Eye,
  EyeOff,
  Zap,
  Building2,
  Cpu,
  ShieldCheck,
  CheckCircle2,
  Sparkles,
  ArrowRight,
  Sun,
  Moon,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

export const LoginPage: React.FC = () => {
  const { login, error } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [credential, setCredential] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [tier, setTier] = useState<string>("enterprises");
  const [loading, setLoading] = useState(false);

  const metaEnv = (import.meta as { env?: Record<string, unknown> }).env;
  const showDemoAccount =
    !metaEnv || Boolean(metaEnv.DEV) || metaEnv.VITE_ENABLE_DEMO !== "false";

  const blobsData = useMemo(() => {
    return Array.from({ length: 6 }).map(() => ({
      size: Math.random() * 200 + 150,
      left: Math.random() * 80 + 10,
      top: Math.random() * 80 + 10,
      animationDelay: Math.random() * -20,
      animationDuration: Math.random() * 15 + 15,
    }));
  }, []);

  const blobRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mediaQuery.matches) return;

    let rafId: number | null = null;
    const handleMouseMove = (e: MouseEvent) => {
      if (rafId !== null) return;
      rafId = window.requestAnimationFrame(() => {
        const x = e.clientX / window.innerWidth;
        const y = e.clientY / window.innerHeight;

        blobRefs.current.forEach((blob, index) => {
          if (blob) {
            const speed = (index + 1) * 20;
            blob.style.marginLeft = `${x * speed}px`;
            blob.style.marginTop = `${y * speed}px`;
          }
        });
        rafId = null;
      });
    };

    document.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      if (rafId !== null) {
        window.cancelAnimationFrame(rafId);
      }
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!credential || !password || loading) return;
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
    <div className="mercury-wrapper mercury-login">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');

        .mercury-wrapper {
          --filter-goo: url('#mercury-gooey');
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
          min-height: 100vh;
          width: 100%;
          overflow-x: hidden;
          overflow-y: auto;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          padding: 24px 16px;
          transition: background-color 0.35s ease, color 0.35s ease;
        }

        /* Dark Theme Variables */
        html.dark .mercury-wrapper,
        :root:not(.light) .mercury-wrapper {
          --bg: #070709;
          --blob-grad: linear-gradient(135deg, #e0e0e0, #777);
          --blob-opacity: 0.5;
          --card-bg: rgba(18, 18, 22, 0.75);
          --card-border: rgba(255, 255, 255, 0.12);
          --card-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.75);
          --feat-bg: rgba(255, 255, 255, 0.03);
          --feat-border: rgba(255, 255, 255, 0.08);
          --feat-hover-bg: rgba(255, 255, 255, 0.06);
          --text-primary: #ffffff;
          --text-muted: rgba(255, 255, 255, 0.7);
          --text-dim: rgba(255, 255, 255, 0.55);
          --input-border: rgba(255, 255, 255, 0.18);
          --input-color: #ffffff;
          --input-placeholder: rgba(255, 255, 255, 0.28);
          --select-opt-bg: #121217;
          --btn-bg: #ffffff;
          --btn-color: #000000;
          --mercury-drop: #e0e0e0;
          --border-subtle: rgba(255, 255, 255, 0.08);
          --demo-bg: rgba(255, 255, 255, 0.04);
          background-color: var(--bg);
          color: var(--text-primary);
        }

        /* Light Theme Variables */
        html.light .mercury-wrapper {
          --bg: #f4f6f9;
          --blob-grad: linear-gradient(135deg, #f2c65d, #d1d5db);
          --blob-opacity: 0.28;
          --card-bg: rgba(255, 255, 255, 0.88);
          --card-border: rgba(0, 0, 0, 0.08);
          --card-shadow: 0 20px 45px -12px rgba(0, 0, 0, 0.08);
          --feat-bg: rgba(255, 255, 255, 0.78);
          --feat-border: rgba(0, 0, 0, 0.06);
          --feat-hover-bg: rgba(255, 255, 255, 0.95);
          --text-primary: #0f172a;
          --text-muted: #475569;
          --text-dim: #64748b;
          --input-border: rgba(0, 0, 0, 0.16);
          --input-color: #0f172a;
          --input-placeholder: rgba(0, 0, 0, 0.35);
          --select-opt-bg: #ffffff;
          --btn-bg: #0f172a;
          --btn-color: #ffffff;
          --mercury-drop: #f2c65d;
          --border-subtle: rgba(0, 0, 0, 0.08);
          --demo-bg: rgba(242, 198, 93, 0.12);
          background-color: var(--bg);
          color: var(--text-primary);
        }

        .mercury-wrapper * {
          box-sizing: border-box;
          -webkit-font-smoothing: antialiased;
        }

        .mercury-wrapper .stage {
          position: fixed;
          inset: 0;
          width: 100%;
          height: 100%;
          z-index: 0;
          filter: var(--filter-goo);
          opacity: var(--blob-opacity);
          pointer-events: none;
          overflow: hidden;
        }

        .mercury-wrapper .blob {
          position: absolute;
          background: var(--blob-grad);
          border-radius: 50%;
          filter: blur(25px);
          animation: mercury-float 22s infinite alternate ease-in-out;
          box-shadow:
            inset -10px -10px 20px rgba(0, 0, 0, 0.3),
            10px 10px 30px rgba(255, 255, 255, 0.2);
          transition: margin 0.1s ease-out;
          pointer-events: none;
          will-change: transform, margin;
        }

        @keyframes mercury-float {
          0% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(8vw, 15vh) scale(1.15); }
          66% { transform: translate(-5vw, 8vh) scale(0.85); }
          100% { transform: translate(6vw, -8vh) scale(1.1); }
        }

        .mercury-layout-container {
          position: relative;
          z-index: 10;
          width: 100%;
          max-width: 1200px;
          display: grid;
          grid-template-columns: 1fr;
          gap: 40px;
          align-items: center;
          margin: auto;
        }

        @media (min-width: 1024px) {
          .mercury-layout-container {
            grid-template-columns: 1.15fr 0.95fr;
            gap: 64px;
            padding: 32px 24px;
          }
        }

        /* Showcase Column */
        .showcase-column {
          display: flex;
          flex-direction: column;
          gap: 28px;
        }

        @media (max-width: 1023px) {
          .showcase-column {
            display: none;
          }
        }

        .brand-pill {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 6px 14px;
          border-radius: 9999px;
          background: rgba(242, 198, 93, 0.12);
          border: 1px solid rgba(242, 198, 93, 0.3);
          font-family: 'Space Mono', monospace;
          font-size: 11px;
          letter-spacing: 1.5px;
          text-transform: uppercase;
          color: #d97706;
          width: fit-content;
        }
        html.dark .brand-pill {
          color: #f2c65d;
          border-color: rgba(242, 198, 93, 0.35);
        }

        .showcase-heading {
          font-weight: 800;
          font-size: clamp(2rem, 3.5vw, 3.2rem);
          line-height: 1.1;
          letter-spacing: -1.5px;
          margin: 0;
          color: var(--text-primary);
        }

        .showcase-description {
          font-size: 15px;
          line-height: 1.6;
          color: var(--text-muted);
          max-width: 520px;
          margin: 0;
        }

        .feature-cards-grid {
          display: flex;
          flex-direction: column;
          gap: 14px;
          margin-top: 8px;
        }

        .feature-card {
          display: flex;
          align-items: flex-start;
          gap: 14px;
          padding: 14px 18px;
          border-radius: 14px;
          background: var(--feat-bg);
          border: 1px solid var(--feat-border);
          backdrop-filter: blur(14px);
          transition: transform 0.25s, border-color 0.25s, background 0.25s;
        }

        .feature-card:hover {
          transform: translateY(-2px);
          border-color: rgba(242, 198, 93, 0.45);
          background: var(--feat-hover-bg);
        }

        .feature-icon-box {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 36px;
          height: 36px;
          border-radius: 10px;
          background: rgba(242, 198, 93, 0.15);
          color: #d97706;
          flex-shrink: 0;
        }
        html.dark .feature-icon-box {
          color: #f2c65d;
        }

        .feature-title {
          font-weight: 600;
          font-size: 13.5px;
          color: var(--text-primary);
          margin-bottom: 2px;
        }

        .feature-desc {
          font-size: 12px;
          line-height: 1.45;
          color: var(--text-dim);
          margin: 0;
        }

        .status-badge {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          color: var(--text-dim);
          font-family: 'Space Mono', monospace;
        }

        .pulse-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #10b981;
          box-shadow: 0 0 10px #10b981;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0% { transform: scale(0.95); opacity: 0.8; }
          50% { transform: scale(1.2); opacity: 1; }
          100% { transform: scale(0.95); opacity: 0.8; }
        }

        /* Form Card Column */
        .auth-card {
          width: 100%;
          max-width: 460px;
          margin: 0 auto;
          background: var(--card-bg);
          border: 1px solid var(--card-border);
          border-radius: 24px;
          padding: 40px 36px;
          backdrop-filter: blur(24px);
          box-shadow: var(--card-shadow);
        }

        @media (max-width: 480px) {
          .auth-card {
            padding: 30px 20px;
            border-radius: 20px;
          }
        }

        .auth-header {
          margin-bottom: 32px;
          text-align: left;
        }

        .auth-header .brand-id {
          font-family: 'Space Mono', monospace;
          font-size: 10px;
          letter-spacing: 3px;
          text-transform: uppercase;
          color: #d97706;
          margin-bottom: 6px;
          display: block;
        }
        html.dark .auth-header .brand-id {
          color: #f2c65d;
        }

        .auth-header h2 {
          font-weight: 800;
          font-size: 1.85rem;
          line-height: 1.1;
          letter-spacing: -0.5px;
          margin: 0 0 6px 0;
          color: var(--text-primary);
        }

        .auth-header p {
          font-size: 13px;
          color: var(--text-dim);
          margin: 0;
        }

        .mercury-wrapper .error-box {
          font-family: 'Inter', sans-serif;
          background: rgba(220, 38, 38, 0.12);
          border: 1px solid rgba(248, 113, 113, 0.4);
          border-left: 3px solid #ef4444;
          color: #ef4444;
          padding: 12px 14px;
          font-size: 13px;
          line-height: 1.45;
          margin-bottom: 24px;
          border-radius: 8px;
        }
        html.dark .mercury-wrapper .error-box {
          color: #fecaca;
        }

        .mercury-wrapper .form-group {
          position: relative;
          margin-bottom: 26px;
          transition: transform 0.3s cubic-bezier(0.2, 1, 0.3, 1);
        }

        .mercury-wrapper .form-group:focus-within {
          transform: translateX(4px);
        }

        .mercury-wrapper .form-group label {
          display: block;
          font-family: 'Space Mono', monospace;
          font-size: 11px;
          color: var(--text-dim);
          margin-bottom: 8px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .mercury-wrapper .form-group input,
        .mercury-wrapper .form-group select {
          display: block;
          width: 100%;
          background: transparent !important;
          background-color: transparent !important;
          border: none !important;
          border-bottom: 1px solid var(--input-border) !important;
          border-radius: 0 !important;
          box-shadow: none !important;
          color: var(--input-color) !important;
          padding: 10px 0;
          font-size: 16px;
          font-family: 'Inter', sans-serif;
          outline: none !important;
          transition: border-color 0.3s;
          -webkit-appearance: none;
          appearance: none;
        }

        .mercury-wrapper .form-group input:focus,
        .mercury-wrapper .form-group select:focus {
          background: transparent !important;
          background-color: transparent !important;
          outline: none !important;
          box-shadow: none !important;
        }

        .mercury-wrapper .form-group select {
          padding-right: 28px;
          cursor: pointer;
        }

        .mercury-wrapper .form-group select option {
          background-color: var(--select-opt-bg);
          color: var(--text-primary);
          padding: 10px;
        }

        .mercury-wrapper .select-chevron {
          position: absolute;
          right: 4px;
          bottom: 14px;
          pointer-events: none;
          color: var(--text-dim);
          font-size: 10px;
        }

        .mercury-wrapper .form-group input::placeholder {
          color: var(--input-placeholder);
          opacity: 1;
        }

        .mercury-wrapper .password-toggle {
          position: absolute;
          right: 0;
          bottom: 8px;
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          color: var(--text-dim);
          cursor: pointer;
          padding: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: color 0.2s;
        }

        .mercury-wrapper .password-toggle:hover {
          color: var(--text-primary);
        }

        .mercury-wrapper .input-glow {
          position: absolute;
          bottom: 0;
          left: 0;
          width: 0%;
          height: 2px;
          background: #f2c65d;
          box-shadow: 0 0 12px rgba(242, 198, 93, 0.8);
          pointer-events: none;
          transition: width 0.4s cubic-bezier(0.2, 1, 0.3, 1);
        }

        .mercury-wrapper .form-group input:focus ~ .input-glow,
        .mercury-wrapper .form-group select:focus ~ .input-glow,
        .mercury-wrapper .form-group:focus-within .input-glow {
          width: 100%;
        }

        .mercury-wrapper .submit-wrap {
          margin-top: 36px;
          position: relative;
          filter: var(--filter-goo);
        }

        .mercury-wrapper .btn-base {
          background: var(--btn-bg);
          color: var(--btn-color);
          border: none;
          border-radius: 12px;
          padding: 16px 28px;
          font-size: 13px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1.5px;
          cursor: pointer;
          width: 100%;
          position: relative;
          z-index: 2;
          transition: letter-spacing 0.3s, opacity 0.3s, background-color 0.3s;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
        }

        .mercury-wrapper .btn-base:hover:not(:disabled) {
          letter-spacing: 2.5px;
          opacity: 0.95;
        }

        .mercury-wrapper .btn-base:disabled {
          opacity: 0.65;
          cursor: not-allowed;
        }

        .mercury-wrapper .mercury-drop {
          position: absolute;
          top: 50%;
          left: 50%;
          width: 100%;
          height: 100%;
          background: var(--mercury-drop);
          transform: translate(-50%, -50%);
          z-index: 1;
          border-radius: 20px;
          transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
          pointer-events: none;
        }

        .mercury-wrapper .submit-wrap:hover .mercury-drop {
          transform: translate(-50%, -50%) scale(1.03, 1.15);
          filter: brightness(1.15);
        }

        .mercury-wrapper .footer-nav {
          margin-top: 28px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          font-family: 'Space Mono', monospace;
          font-size: 11px;
          border-top: 1px solid var(--border-subtle);
          padding-top: 20px;
        }

        .mercury-wrapper .demo-btn {
          background: var(--demo-bg);
          border: 1px dashed rgba(242, 198, 93, 0.45);
          border-radius: 10px;
          padding: 10px 14px;
          color: #d97706;
          font-family: 'Space Mono', monospace;
          font-size: 11px;
          letter-spacing: 0.5px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          transition: all 0.25s;
          width: 100%;
        }
        html.dark .mercury-wrapper .demo-btn {
          color: #f2c65d;
        }

        .mercury-wrapper .demo-btn:hover {
          background: rgba(242, 198, 93, 0.2);
          border-color: #f2c65d;
        }

        .enterprise-badge-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 11px;
          color: var(--text-dim);
          margin-top: 4px;
        }

        /* Top Theme Toggle Button */
        .login-theme-toggle {
          position: absolute;
          top: 24px;
          right: 24px;
          z-index: 50;
          display: flex;
          align-items: center;
          justify-content: center;
          height: 40px;
          width: 40px;
          border-radius: 12px;
          border: 1px solid var(--card-border);
          background: var(--card-bg);
          backdrop-filter: blur(16px);
          cursor: pointer;
          transition: all 0.25s;
          color: var(--text-primary);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }

        .login-theme-toggle:hover {
          transform: scale(1.05);
          border-color: rgba(242, 198, 93, 0.5);
        }

        @media (prefers-reduced-motion: reduce) {
          .mercury-wrapper .blob {
            animation: none;
            transition: none;
          }
          .mercury-wrapper .form-group,
          .mercury-wrapper .input-glow,
          .mercury-wrapper .mercury-drop,
          .mercury-wrapper .btn-base,
          .feature-card {
            transition: none;
          }
        }
      `}</style>

      {/* Floating Theme Toggle on Login Page */}
      <button
        type="button"
        onClick={toggleTheme}
        className="login-theme-toggle"
        aria-label={theme === "dark" ? "Chuyển sang chế độ sáng" : "Chuyển sang chế độ tối"}
        title={theme === "dark" ? "Chuyển sang Light Mode" : "Chuyển sang Dark Mode"}
      >
        {theme === "dark" ? (
          <Sun className="h-4 w-4 text-amber-400" />
        ) : (
          <Moon className="h-4 w-4 text-slate-700" />
        )}
      </button>

      <svg className="absolute w-0 h-0 pointer-events-none" aria-hidden="true">
        <defs>
          <filter id="mercury-gooey">
            <feGaussianBlur in="SourceGraphic" stdDeviation="12" result="blur" />
            <feColorMatrix
              in="blur"
              mode="matrix"
              values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 19 -9"
              result="goo"
            />
            <feComposite in="SourceGraphic" in2="goo" operator="atop" />
          </filter>
        </defs>
      </svg>

      <div className="stage" id="stage" aria-hidden="true">
        {blobsData.map((data, index) => (
          <div
            key={index}
            ref={(el) => {
              blobRefs.current[index] = el;
            }}
            className="blob"
            style={{
              width: `${data.size}px`,
              height: `${data.size}px`,
              left: `${data.left}%`,
              top: `${data.top}%`,
              animationDelay: `${data.animationDelay}s`,
              animationDuration: `${data.animationDuration}s`,
            }}
          />
        ))}
      </div>

      <div className="mercury-layout-container">
        {/* Left Column: Enterprise Showcase & Branding (Desktop Web Real Estate) */}
        <section className="showcase-column" aria-label="Giới thiệu hệ thống SGOD">
          <div className="brand-pill">
            <Sparkles className="h-3.5 w-3.5 text-amber-500" />
            <span>SGOD AI ASSET ECOSYSTEM</span>
          </div>

          <h1 className="showcase-heading">
            Trợ lý AI Quản trị &<br />Vận hành Tài sản Số
          </h1>

          <p className="showcase-description">
            Nền tảng hội thoại thông minh kết nối trực tiếp cơ sở dữ liệu doanh nghiệp,
            tự động hóa truy vấn kho bãi, kiểm kê và phân bổ tài sản tức thì.
          </p>

          <div className="feature-cards-grid">
            <div className="feature-card">
              <div className="feature-icon-box">
                <Cpu className="h-4 w-4" />
              </div>
              <div>
                <div className="feature-title">AI Function Calling thời gian thực</div>
                <p className="feature-desc">
                  Trực tiếp thực thi API backend SGOD để tra cứu tài sản, kiểm tra vị trí kho và tính toán số liệu.
                </p>
              </div>
            </div>

            <div className="feature-card">
              <div className="feature-icon-box">
                <Building2 className="h-4 w-4" />
              </div>
              <div>
                <div className="feature-title">Kiến trúc Đa Doanh nghiệp & Chi nhánh</div>
                <p className="feature-desc">
                  Quản lý phân tầng từ Tập đoàn, Chi nhánh trực thuộc đến từng Nhân viên theo chuẩn Multi-tenant.
                </p>
              </div>
            </div>

            <div className="feature-card">
              <div className="feature-icon-box">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div>
                <div className="feature-title">Bảo mật & Kiểm soát Phân quyền</div>
                <p className="feature-desc">
                  Bảo vệ dữ liệu tài sản nghiêm ngặt với xác thực JWT và phân định quyền truy cập vai trò (RBAC).
                </p>
              </div>
            </div>
          </div>

          <div className="status-badge">
            <span className="pulse-dot" />
            <span>Hệ thống Gateway Sẵn sàng • Uptime 99.9% • Web Portal v1.0</span>
          </div>
        </section>

        {/* Right Column: Modern Glassmorphic Login Form */}
        <main className="auth-card">
          <header className="auth-header">
            <span className="brand-id">SGOD / SECURE ACCESS</span>
            <h2>Đăng nhập Hệ thống</h2>
            <p>Vui lòng chọn tầng quyền và nhập thông tin tài khoản</p>
          </header>

          {error && (
            <div className="error-box" role="alert">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="sgod-tier">Tầng truy cập (Tier)</label>
              <select
                id="sgod-tier"
                value={tier}
                onChange={(e) => setTier(e.target.value)}
              >
                <option value="enterprises">
                  Quản trị viên Doanh nghiệp (Enterprise Admin)
                </option>
                <option value="enterprise-users">
                  Nhân viên Doanh nghiệp (Employee)
                </option>
                <option value="sub-enterprises">
                  Chi nhánh trực thuộc (Sub-Enterprise)
                </option>
                <option value="">Tự động nhận diện theo tài khoản</option>
              </select>
              <span className="select-chevron">▼</span>
              <div className="input-glow" />
            </div>

            <div className="form-group">
              <label htmlFor="sgod-credential">Email hoặc tên đăng nhập</label>
              <input
                id="sgod-credential"
                name="credential"
                type="text"
                autoComplete="username"
                value={credential}
                onChange={(e) => setCredential(e.target.value)}
                placeholder="admin@enterprise.vn hoặc username"
                required
              />
              <div className="input-glow" />
            </div>

            <div className="form-group">
              <label htmlFor="sgod-password">Mật khẩu</label>
              <input
                id="sgod-password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Nhập mật khẩu truy cập..."
                required
                style={{ paddingRight: "36px" }}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((prev) => !prev)}
                aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                title={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
              <div className="input-glow" />
            </div>

            <div className="submit-wrap">
              <div className="mercury-drop" />
              <button type="submit" disabled={loading} className="btn-base">
                <span>{loading ? "Đang xác thực..." : "Đăng nhập hệ thống"}</span>
                {!loading && <ArrowRight className="h-4 w-4" />}
              </button>
            </div>
          </form>

          <footer className="footer-nav">
            {showDemoAccount && (
              <button
                type="button"
                onClick={handleFillDemo}
                className="demo-btn"
                title="Tự động điền tài khoản thử nghiệm"
              >
                <Zap className="h-3.5 w-3.5" />
                <span>Điền nhanh tài khoản thử nghiệm mẫu (Enterprise Admin)</span>
              </button>
            )}

            <div className="enterprise-badge-row">
              <span className="flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                <span>Mã hóa SSL/TLS 256-bit</span>
              </span>
              <span>SGOD AI v1.0</span>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
};

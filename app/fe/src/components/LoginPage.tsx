import React, { useEffect, useMemo, useRef, useState } from "react";
import { Eye, EyeOff, Zap } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export const LoginPage: React.FC = () => {
  const { login, error } = useAuth();
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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Space+Mono:wght@400;700&display=swap');

        .mercury-wrapper {
          --bg: #050505;
          --mercury: #e0e0e0;
          --mercury-dark: #666666;
          --accent: #ffffff;
          --text-dim: rgba(255, 255, 255, 0.5);
          --filter-goo: url('#mercury-gooey');

          background-color: var(--bg);
          color: var(--accent);
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
          min-height: 100vh;
          width: 100%;
          overflow-x: hidden;
          overflow-y: auto;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
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
          opacity: 0.6;
          pointer-events: none;
          overflow: hidden;
        }

        .mercury-wrapper .blob {
          position: absolute;
          background: linear-gradient(135deg, var(--mercury), #888);
          border-radius: 50%;
          filter: blur(20px);
          animation: mercury-float 20s infinite alternate ease-in-out;
          box-shadow:
            inset -10px -10px 20px rgba(0, 0, 0, 0.5),
            10px 10px 30px rgba(255, 255, 255, 0.2);
          transition: margin 0.1s ease-out;
          pointer-events: none;
          will-change: transform, margin;
        }

        @keyframes mercury-float {
          0% {
            transform: translate(0, 0) scale(1);
          }
          33% {
            transform: translate(10vw, 20vh) scale(1.2);
          }
          66% {
            transform: translate(-5vw, 10vh) scale(0.8);
          }
          100% {
            transform: translate(5vw, -10vh) scale(1.1);
          }
        }

        .mercury-wrapper .auth-container {
          position: relative;
          z-index: 10;
          width: 100%;
          max-width: 440px;
          padding: 40px;
        }

        @media (max-width: 480px) {
          .mercury-wrapper .auth-container {
            padding: 28px 20px;
          }
        }

        .mercury-wrapper .header {
          margin-bottom: 60px;
          text-align: left;
        }

        .mercury-wrapper .brand-id {
          font-family: 'Space Mono', monospace;
          font-size: 10px;
          letter-spacing: 4px;
          text-transform: uppercase;
          color: var(--text-dim);
          margin-bottom: 8px;
          display: block;
        }

        .mercury-wrapper .header h1 {
          font-weight: 800;
          font-size: 3rem;
          line-height: 0.9;
          letter-spacing: -2px;
          margin-left: -4px;
          margin-top: 0;
          margin-bottom: 0;
          color: var(--accent);
        }

        .mercury-wrapper .error-box {
          font-family: 'Inter', sans-serif;
          background: rgba(220, 38, 38, 0.12);
          border: 1px solid rgba(248, 113, 113, 0.4);
          border-left: 3px solid #f87171;
          color: #fecaca;
          padding: 12px 14px;
          font-size: 13px;
          line-height: 1.45;
          margin-bottom: 30px;
        }

        .mercury-wrapper .form-group {
          position: relative;
          margin-bottom: 30px;
          transition: transform 0.4s cubic-bezier(0.2, 1, 0.3, 1);
        }

        .mercury-wrapper .form-group:focus-within {
          transform: translateX(10px);
        }

        .mercury-wrapper .form-group label {
          display: block;
          font-family: 'Space Mono', monospace;
          font-size: 11px;
          color: var(--text-dim);
          margin-bottom: 12px;
          text-transform: uppercase;
        }

        .mercury-wrapper .form-group input,
        .mercury-wrapper .form-group select {
          display: block;
          width: 100%;
          background: transparent !important;
          background-color: transparent !important;
          border: none !important;
          border-bottom: 1px solid rgba(255, 255, 255, 0.15) !important;
          border-radius: 0 !important;
          box-shadow: none !important;
          color: #ffffff !important;
          padding: 12px 0;
          font-size: 18px;
          font-family: 'Inter', sans-serif;
          outline: none !important;
          transition: border-color 0.4s;
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
          background-color: #0a0a0a;
          color: #ffffff;
          padding: 10px;
        }

        .mercury-wrapper .select-chevron {
          position: absolute;
          right: 4px;
          bottom: 16px;
          pointer-events: none;
          color: var(--text-dim);
          font-family: 'Space Mono', monospace;
          font-size: 10px;
        }

        .mercury-wrapper .form-group input::placeholder {
          color: rgba(255, 255, 255, 0.3);
          opacity: 1;
        }

        /* Chrome / Safari / Edge autofill transparent fix */
        .mercury-wrapper .form-group input:-webkit-autofill,
        .mercury-wrapper .form-group input:-webkit-autofill:hover,
        .mercury-wrapper .form-group input:-webkit-autofill:focus,
        .mercury-wrapper .form-group input:-webkit-autofill:active {
          -webkit-text-fill-color: #ffffff !important;
          caret-color: #ffffff !important;
          background: transparent !important;
          background-color: transparent !important;
          -webkit-box-shadow: 0 0 0 1000px rgba(5, 5, 5, 0) inset !important;
          box-shadow: 0 0 0 1000px rgba(5, 5, 5, 0) inset !important;
          border: none !important;
          border-bottom: 1px solid rgba(255, 255, 255, 0.15) !important;
          border-radius: 0 !important;
          transition: background-color 99999s ease-in-out 0s, color 99999s ease-in-out 0s !important;
        }

        .mercury-wrapper .password-toggle {
          position: absolute;
          right: 0;
          bottom: 10px;
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
          color: var(--accent);
        }

        .mercury-wrapper .input-glow {
          position: absolute;
          bottom: 0;
          left: 0;
          width: 0%;
          height: 2px;
          background: #e0e0e0;
          box-shadow: 0 0 15px rgba(224, 224, 224, 0.8);
          pointer-events: none;
          transition: width 0.6s cubic-bezier(0.2, 1, 0.3, 1);
        }

        .mercury-wrapper .form-group input:focus ~ .input-glow,
        .mercury-wrapper .form-group select:focus ~ .input-glow,
        .mercury-wrapper .form-group:focus-within .input-glow {
          width: 100%;
        }

        .mercury-wrapper .submit-wrap {
          margin-top: 50px;
          position: relative;
          filter: var(--filter-goo);
        }

        .mercury-wrapper .btn-base {
          background: var(--accent);
          color: #000000;
          border: none;
          padding: 20px 40px;
          font-size: 14px;
          font-weight: 800;
          text-transform: uppercase;
          letter-spacing: 2px;
          cursor: pointer;
          width: 100%;
          position: relative;
          z-index: 2;
          transition: letter-spacing 0.3s, opacity 0.3s;
        }

        .mercury-wrapper .btn-base:hover:not(:disabled) {
          letter-spacing: 4px;
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
          background: var(--mercury);
          transform: translate(-50%, -50%);
          z-index: 1;
          border-radius: 50px;
          transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
          pointer-events: none;
        }

        .mercury-wrapper .submit-wrap:hover .mercury-drop {
          transform: translate(-50%, -50%) scale(1.05, 1.2);
          filter: brightness(1.2);
        }

        .mercury-wrapper .footer-nav {
          margin-top: 40px;
          display: flex;
          justify-content: space-between;
          font-family: 'Space Mono', monospace;
          font-size: 10px;
        }

        .mercury-wrapper .demo-btn {
          background: transparent;
          border: none;
          padding: 0;
          color: var(--text-dim);
          font-family: 'Space Mono', monospace;
          font-size: 10px;
          letter-spacing: 1px;
          text-transform: uppercase;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 6px;
          transition: color 0.3s;
        }

        .mercury-wrapper .demo-btn:hover {
          color: var(--accent);
        }

        .mercury-wrapper .svg-filter-hidden {
          position: absolute;
          width: 0;
          height: 0;
          pointer-events: none;
        }

        @media (prefers-reduced-motion: reduce) {
          .mercury-wrapper .blob {
            animation: none;
            transition: none;
          }
          .mercury-wrapper .form-group,
          .mercury-wrapper .input-glow,
          .mercury-wrapper .mercury-drop,
          .mercury-wrapper .btn-base {
            transition: none;
          }
        }
      `}</style>

      <svg className="svg-filter-hidden" aria-hidden="true">
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

      <main className="auth-container">
        <header className="header">
          <span className="brand-id">SGOD / AI ASSISTANT</span>
          <h1>
            SGOD
            <br />
            ACCESS
          </h1>
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
              placeholder="thuongpx2007@gmail.com"
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
              placeholder="••••••••"
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
              {loading ? "Đang xác thực..." : "Đăng nhập"}
            </button>
          </div>
        </form>

        {showDemoAccount && (
          <footer className="footer-nav">
            <button
              type="button"
              onClick={handleFillDemo}
              className="demo-btn"
            >
              <Zap className="h-3 w-3" />
              <span>Điền tài khoản mẫu (thuongpx2007)</span>
            </button>
          </footer>
        )}
      </main>
    </div>
  );
};

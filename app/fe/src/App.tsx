import React from 'react';
import { useAuth } from './context/AuthContext';
import { LoginPage } from './components/LoginPage';
import { ChatWidget } from './components/ChatWidget';

export const App: React.FC = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', fontFamily: 'sans-serif' }}>
        <p>Đang kiểm tra trạng thái đăng nhập...</p>
      </div>
    );
  }

  return (
    <div>
      {isAuthenticated ? <ChatWidget /> : <LoginPage />}
    </div>
  );
};

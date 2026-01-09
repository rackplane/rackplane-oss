import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import LoginModal from './LoginModal';
import { AuthProvider } from '../contexts/AuthContext';

// Mock axios before importing anything that uses it
jest.mock('axios', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
    get: jest.fn(),
    defaults: {
      headers: {
        common: {}
      }
    }
  },
}));

// Mock the API_URL
jest.mock('../config/api', () => ({
  API_URL: 'http://localhost:8000'
}));

// Helper to render with AuthProvider
const renderWithAuth = (component: React.ReactElement) => {
  return render(<AuthProvider>{component}</AuthProvider>);
};

describe('LoginModal', () => {
  const mockOnClose = jest.fn();
  const mockLogin = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    // Reset environment variables
    delete process.env.REACT_APP_DEMO_MODE;
    delete process.env.REACT_APP_DEMO_USERNAME;
    delete process.env.REACT_APP_DEMO_PASSWORD;
  });

  describe('Normal mode (demo mode disabled)', () => {
    it('renders login form when demo mode is not enabled', () => {
      renderWithAuth(<LoginModal isOpen={true} onClose={mockOnClose} />);
      
      expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    });

    it('does not show demo credentials box in normal mode', () => {
      renderWithAuth(<LoginModal isOpen={true} onClose={mockOnClose} />);
      
      expect(screen.queryByText(/demo credentials/i)).not.toBeInTheDocument();
    });
  });

  describe('Demo mode (REACT_APP_DEMO_MODE=true)', () => {
    beforeEach(() => {
      process.env.REACT_APP_DEMO_MODE = 'true';
      process.env.REACT_APP_DEMO_USERNAME = 'demo-user';
      process.env.REACT_APP_DEMO_PASSWORD = 'demo-pass';
    });

    it('shows demo credentials when demo mode is enabled', () => {
      renderWithAuth(<LoginModal isOpen={true} onClose={mockOnClose} />);
      
      expect(screen.getByText(/demo credentials/i)).toBeInTheDocument();
      expect(screen.getByText(/demo-user/i)).toBeInTheDocument();
      expect(screen.getByText(/demo-pass/i)).toBeInTheDocument();
    });

    it('hides login form in demo mode', () => {
      renderWithAuth(<LoginModal isOpen={true} onClose={mockOnClose} />);
      
      expect(screen.queryByLabelText(/username/i)).not.toBeInTheDocument();
      expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
    });

    it('shows "Login to Demo" button in demo mode', () => {
      renderWithAuth(<LoginModal isOpen={true} onClose={mockOnClose} />);
      
      expect(screen.getByRole('button', { name: /login to demo/i })).toBeInTheDocument();
    });

    it('uses default credentials when env vars not set', () => {
      delete process.env.REACT_APP_DEMO_USERNAME;
      delete process.env.REACT_APP_DEMO_PASSWORD;
      process.env.REACT_APP_DEMO_MODE = 'true';
      
      renderWithAuth(<LoginModal isOpen={true} onClose={mockOnClose} />);
      
      // Check that demo credentials are shown (both username and password default to 'admin')
      expect(screen.getByText(/demo credentials/i)).toBeInTheDocument();
      const usernameElements = screen.getAllByText(/admin/i);
      expect(usernameElements.length).toBeGreaterThanOrEqual(1); // At least username or password shows 'admin'
    });
  });

  it('does not render when isOpen is false', () => {
    const { container } = renderWithAuth(<LoginModal isOpen={false} onClose={mockOnClose} />);
    expect(container.firstChild).toBeNull();
  });
});


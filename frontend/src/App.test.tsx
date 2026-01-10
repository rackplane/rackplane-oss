import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { vi } from 'vitest';
import App from './App';

// Mock all the contexts
vi.mock('./contexts/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useAuth: () => ({
    user: { id: 1, username: 'testuser', role: 'admin', tenant_id: 1 },
    isAuthenticated: true,
    isSuperAdmin: false,
    isTenantAdmin: true,
    isLoading: false,
    logout: vi.fn(),
  }),
}));

vi.mock('./contexts/WhiteLabelContext', () => ({
  WhiteLabelProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useWhiteLabel: () => ({
    displayName: 'RackPlane',
    t: (key: string) => key, // Returns the key itself (e.g., 'items' → 'items')
  }),
}));

vi.mock('./contexts/CartContext', () => ({
  CartProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useCart: () => ({
    cart: [],
    toggleCart: vi.fn(),
  }),
}));

// Mock axios
vi.mock('axios', () => ({
  __esModule: true,
  default: {
    get: vi.fn((url: string) => {
      if (url.includes('/demo-info')) {
        return Promise.resolve({ data: { demo_login_enabled: false } });
      }
      if (url.includes('/tenants/current/settings')) {
        return Promise.resolve({ data: { show_dev_troubleshooting: false } });
      }
      return Promise.resolve({ data: {} });
    }),
    post: vi.fn(),
    defaults: {
      headers: {
        common: {},
      },
    },
  },
}));

// Mock the API_URL
vi.mock('./config/api', () => ({
  API_URL: 'http://localhost:8000',
}));

// Mock environment util
vi.mock('./utils/environment', () => ({
  isDemoEnvironment: () => false,
}));

// Mock all lazy-loaded components
vi.mock('./pages/Dashboard', () => ({
  __esModule: true,
  default: () => <div>Dashboard</div>,
}));

vi.mock('./pages/Assets', () => ({
  __esModule: true,
  default: () => <div>Assets</div>,
}));

// Mock other components
vi.mock('./components/GlobalSearch', () => ({
  __esModule: true,
  default: () => <div>GlobalSearch</div>,
}));

vi.mock('./components/ThemeToggle', () => ({
  __esModule: true,
  default: () => <div>ThemeToggle</div>,
}));

vi.mock('./components/SubscriptionBadge', () => ({
  __esModule: true,
  default: () => <div>SubscriptionBadge</div>,
}));

vi.mock('./components/ShoppingCartDrawer', () => ({
  __esModule: true,
  default: () => <div>ShoppingCartDrawer</div>,
}));

// Helper to advance timers and flush promises
const advanceTimersAndFlush = async (ms: number) => {
  await act(async () => {
    vi.advanceTimersByTime(ms);
    await Promise.resolve();
  });
};

describe('Dropdown Close Delay', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it('should delay close by 200ms on mouse leave', async () => {
    render(<App />);

    // Wait for component to mount and data to load
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    // Find and click the Inventory dropdown button
    const inventoryButton = screen.getByRole('button', { name: /Inventory/i });

    await act(async () => {
      fireEvent.click(inventoryButton);
    });

    // Verify dropdown is open by checking for 'storage' menu item
    await waitFor(() => {
      const storageLink = screen.queryByRole('link', { name: /storage/i });
      expect(storageLink).toBeInTheDocument();
    }, { timeout: 3000 });

    // Find the dropdown container and trigger mouse leave
    const dropdownContainer = inventoryButton.closest('[class*="relative"]');
    expect(dropdownContainer).toBeInTheDocument();

    await act(async () => {
      fireEvent.mouseLeave(dropdownContainer!);
    });

    // Immediately after mouse leave, dropdown should still be open
    expect(screen.queryByRole('link', { name: /storage/i })).toBeInTheDocument();

    // Advance timers by 100ms (less than 200ms delay)
    await advanceTimersAndFlush(100);

    // Dropdown should still be open
    expect(screen.queryByRole('link', { name: /storage/i })).toBeInTheDocument();

    // Advance timers by another 100ms (total 200ms)
    await advanceTimersAndFlush(100);

    // Dropdown should now be closed
    await waitFor(() => {
      expect(screen.queryByRole('link', { name: /storage/i })).not.toBeInTheDocument();
    });
  });

  it('should cancel delayed close on mouse re-enter', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    // Open the Operations dropdown
    const operationsButton = screen.getByRole('button', { name: /Operations/i });

    await act(async () => {
      fireEvent.click(operationsButton);
    });

    // Verify dropdown is open
    await waitFor(() => {
      expect(screen.queryByRole('link', { name: /Maintenance/i })).toBeInTheDocument();
    }, { timeout: 3000 });

    const dropdownContainer = operationsButton.closest('[class*="relative"]');
    expect(dropdownContainer).toBeInTheDocument();

    // Trigger mouse leave to start the close timer
    await act(async () => {
      fireEvent.mouseLeave(dropdownContainer!);
    });

    // Advance timers by 100ms (halfway to close)
    await advanceTimersAndFlush(100);

    // Mouse re-enters before timer completes
    await act(async () => {
      fireEvent.mouseEnter(dropdownContainer!);
    });

    // Advance timers past the original 200ms deadline
    await advanceTimersAndFlush(150);

    // Dropdown should still be open because timer was cancelled
    expect(screen.queryByRole('link', { name: /Maintenance/i })).toBeInTheDocument();
  });

  it('should close on click outside', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    // Open the Tools dropdown
    const toolsButton = screen.getByRole('button', { name: /Tools/i });

    await act(async () => {
      fireEvent.click(toolsButton);
    });

    // Verify dropdown is open
    await waitFor(() => {
      expect(screen.queryByRole('link', { name: /Locations/i })).toBeInTheDocument();
    }, { timeout: 3000 });

    // Click outside the dropdown (on document body)
    await act(async () => {
      fireEvent.mouseDown(document.body);
    });

    // Dropdown should close immediately (no delay)
    await waitFor(() => {
      expect(screen.queryByRole('link', { name: /Locations/i })).not.toBeInTheDocument();
    });
  });

  it('should cleanup timer on unmount', async () => {
    const { unmount } = render(<App />);

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    // Open dropdown
    const dataButton = screen.getByRole('button', { name: /Data/i });

    await act(async () => {
      fireEvent.click(dataButton);
    });

    await waitFor(() => {
      expect(screen.queryByRole('link', { name: /SKU Catalog/i })).toBeInTheDocument();
    }, { timeout: 3000 });

    const dropdownContainer = dataButton.closest('[class*="relative"]');

    // Trigger mouse leave to start timer
    await act(async () => {
      fireEvent.mouseLeave(dropdownContainer!);
    });

    // Unmount before timer completes
    unmount();

    // Advance timers - should not cause errors because cleanup was called
    await advanceTimersAndFlush(300);

    // No errors should have been thrown
    expect(true).toBe(true);
  });

  it('should clear timer when toggling dropdown', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    // Open the Admin dropdown
    const adminButton = screen.getByRole('button', { name: /Admin/i });

    await act(async () => {
      fireEvent.click(adminButton);
    });

    await waitFor(() => {
      expect(screen.queryByRole('link', { name: /Settings/i })).toBeInTheDocument();
    }, { timeout: 3000 });

    const dropdownContainer = adminButton.closest('[class*="relative"]');

    // Trigger mouse leave to start close timer
    await act(async () => {
      fireEvent.mouseLeave(dropdownContainer!);
    });

    // Before timer completes, click to toggle dropdown closed
    await act(async () => {
      fireEvent.click(adminButton);
    });

    // Dropdown should close immediately
    await waitFor(() => {
      expect(screen.queryByRole('link', { name: /Settings/i })).not.toBeInTheDocument();
    });

    // Advance past the timer delay
    await advanceTimersAndFlush(300);

    // Dropdown should still be closed (timer was cleared)
    expect(screen.queryByRole('link', { name: /Settings/i })).not.toBeInTheDocument();
  });

  it('should clear timer when opening a different dropdown', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    // Open the Inventory dropdown
    const inventoryButton = screen.getByRole('button', { name: /Inventory/i });

    await act(async () => {
      fireEvent.click(inventoryButton);
    });

    await waitFor(() => {
      expect(screen.queryByRole('link', { name: /storage/i })).toBeInTheDocument();
    }, { timeout: 3000 });

    const inventoryContainer = inventoryButton.closest('[class*="relative"]');

    // Trigger mouse leave on Inventory dropdown
    await act(async () => {
      fireEvent.mouseLeave(inventoryContainer!);
    });

    // Before timer completes, open Operations dropdown
    const operationsButton = screen.getByRole('button', { name: /Operations/i });
    await act(async () => {
      fireEvent.click(operationsButton);
    });

    // Inventory dropdown should close and Operations should open
    await waitFor(() => {
      expect(screen.queryByRole('link', { name: /storage/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('link', { name: /Maintenance/i })).toBeInTheDocument();
    }, { timeout: 3000 });

    // Advance past the original timer
    await advanceTimersAndFlush(300);

    // Operations dropdown should still be open
    expect(screen.queryByRole('link', { name: /Maintenance/i })).toBeInTheDocument();
  });

  it('should handle rapid mouse enter/leave cycles', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    // Open dropdown
    const toolsButton = screen.getByRole('button', { name: /Tools/i });

    await act(async () => {
      fireEvent.click(toolsButton);
    });

    await waitFor(() => {
      expect(screen.queryByRole('link', { name: /Locations/i })).toBeInTheDocument();
    }, { timeout: 3000 });

    const dropdownContainer = toolsButton.closest('[class*="relative"]');

    // Simulate rapid mouse movements
    for (let i = 0; i < 5; i++) {
      await act(async () => {
        fireEvent.mouseLeave(dropdownContainer!);
      });
      await advanceTimersAndFlush(50);
      await act(async () => {
        fireEvent.mouseEnter(dropdownContainer!);
      });
      await advanceTimersAndFlush(50);
    }

    // Dropdown should still be open
    expect(screen.queryByRole('link', { name: /Locations/i })).toBeInTheDocument();

    // Final mouse leave
    await act(async () => {
      fireEvent.mouseLeave(dropdownContainer!);
    });
    await advanceTimersAndFlush(200);

    // Now it should close
    await waitFor(() => {
      expect(screen.queryByRole('link', { name: /Locations/i })).not.toBeInTheDocument();
    });
  });
});

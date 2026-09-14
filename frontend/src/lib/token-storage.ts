const ACCESS_TOKEN_KEY = "taxplatform.access_token";
const REFRESH_TOKEN_KEY = "taxplatform.refresh_token";

/**
 * Tokens are kept in localStorage for Phase 1 simplicity. This is a known
 * tradeoff (XSS exposure) versus httpOnly cookies; a future phase can move
 * to cookie-based storage without changing the rest of the auth flow, since
 * all reads/writes go through this module.
 */
export const tokenStorage = {
  getAccessToken: (): string | null => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: (): string | null => localStorage.getItem(REFRESH_TOKEN_KEY),
  setTokens: (accessToken: string, refreshToken: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

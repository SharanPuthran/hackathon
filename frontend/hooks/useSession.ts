/**
 * Session Management Hook
 * 
 * Manages session state for multi-turn conversations with the API.
 * Optionally persists session to localStorage for recovery after page refresh.
 */

import { useState, useEffect } from 'react';

export interface SessionState {
    sessionId: string | null;
    isActive: boolean;
}

export interface UseSessionReturn {
    sessionId: string | null;
    setSessionId: (id: string) => void;
    clearSession: () => void;
    isActive: boolean;
}

const SESSION_STORAGE_KEY = 'skymarshal_session_id';
const SESSION_TIMESTAMP_KEY = 'skymarshal_session_timestamp';
const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes

/**
 * Hook for managing session state
 * 
 * Features:
 * - Stores session ID in state
 * - Optionally persists to localStorage
 * - Automatically clears expired sessions
 * - Provides session active status
 */
export function useSession(persistToStorage = false): UseSessionReturn {
    const [sessionId, setSessionIdState] = useState<string | null>(null);
    const [isActive, setIsActive] = useState<boolean>(false);

    // Load session from localStorage on mount (if persistence is enabled)
    useEffect(() => {
        if (!persistToStorage) return;

        try {
            const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY);
            const storedTimestamp = localStorage.getItem(SESSION_TIMESTAMP_KEY);

            if (storedSessionId && storedTimestamp) {
                const timestamp = parseInt(storedTimestamp, 10);
                const now = Date.now();

                // Check if session has expired
                if (now - timestamp < SESSION_TIMEOUT_MS) {
                    setSessionIdState(storedSessionId);
                    setIsActive(true);
                } else {
                    // Session expired, clear it
                    localStorage.removeItem(SESSION_STORAGE_KEY);
                    localStorage.removeItem(SESSION_TIMESTAMP_KEY);
                }
            }
        } catch (error) {
            console.error('Failed to load session from localStorage:', error);
        }
    }, [persistToStorage]);

    // Update isActive when sessionId changes
    useEffect(() => {
        setIsActive(sessionId !== null);
    }, [sessionId]);

    /**
     * Set the session ID
     */
    const setSessionId = (id: string) => {
        setSessionIdState(id);
        setIsActive(true);

        // Persist to localStorage if enabled
        if (persistToStorage) {
            try {
                localStorage.setItem(SESSION_STORAGE_KEY, id);
                localStorage.setItem(SESSION_TIMESTAMP_KEY, Date.now().toString());
            } catch (error) {
                console.error('Failed to persist session to localStorage:', error);
            }
        }
    };

    /**
     * Clear the session
     */
    const clearSession = () => {
        setSessionIdState(null);
        setIsActive(false);

        // Clear from localStorage if persistence is enabled
        if (persistToStorage) {
            try {
                localStorage.removeItem(SESSION_STORAGE_KEY);
                localStorage.removeItem(SESSION_TIMESTAMP_KEY);
            } catch (error) {
                console.error('Failed to clear session from localStorage:', error);
            }
        }
    };

    return {
        sessionId,
        setSessionId,
        clearSession,
        isActive,
    };
}

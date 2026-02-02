/**
 * API Hook
 * 
 * React hook for API interactions with async polling.
 * Integrates with session management for multi-turn conversations.
 */

import { useState, useCallback } from 'react';
import { AsyncAPIService, StatusResponse } from '../services/apiAsync';
import { useSession } from './useSession';

export interface UseAPIReturn {
    invoke: (prompt: string) => Promise<StatusResponse>;
    loading: boolean;
    progress: string;
    error: string | null;
    clearError: () => void;
}

/**
 * Hook for API interactions with async polling
 * 
 * Features:
 * - Manages loading and error states
 * - Integrates with session management
 * - Provides invoke function with polling
 * - Shows progress during polling
 * - Handles errors gracefully
 */
export function useAPI(): UseAPIReturn {
    const [loading, setLoading] = useState<boolean>(false);
    const [progress, setProgress] = useState<string>('');
    const [error, setError] = useState<string | null>(null);
    const { sessionId, setSessionId } = useSession(false);

    /**
     * Invoke the API with async polling
     */
    const invoke = useCallback(
        async (prompt: string): Promise<StatusResponse> => {
            setLoading(true);
            setProgress('Starting analysis...');
            setError(null);

            try {
                // Create async API service
                const apiService = new AsyncAPIService();

                // Invoke with polling and progress updates
                const response = await apiService.invokeWithPolling(
                    {
                        prompt,
                        session_id: sessionId || undefined,
                    },
                    (elapsedSeconds: number, status: string) => {
                        // Update progress message
                        if (elapsedSeconds < 30) {
                            setProgress(`Analyzing disruption... ${elapsedSeconds}s`);
                        } else if (elapsedSeconds < 60) {
                            setProgress(`Running safety analysis... ${elapsedSeconds}s`);
                        } else if (elapsedSeconds < 120) {
                            setProgress(`Evaluating business impact... ${elapsedSeconds}s`);
                        } else {
                            setProgress(`Finalizing recommendations... ${elapsedSeconds}s`);
                        }
                    }
                );

                // Check if request failed
                if (response.status === 'error') {
                    throw new Error(response.error || 'Processing failed');
                }

                // Update session ID if returned
                if (response.session_id) {
                    setSessionId(response.session_id);
                }

                setLoading(false);
                setProgress('');
                return response;
            } catch (err) {
                setLoading(false);
                setProgress('');

                // Handle errors
                const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
                setError(errorMessage);
                throw err;
            }
        },
        [sessionId, setSessionId]
    );

    /**
     * Clear the error state
     */
    const clearError = useCallback(() => {
        setError(null);
    }, []);

    return {
        invoke,
        loading,
        progress,
        error,
        clearError,
    };
}

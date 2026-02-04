/**
 * Async API Service with Polling
 *
 * Handles async invocation with polling to avoid API Gateway timeouts.
 * The flow:
 * 1. POST /invoke - Returns immediately with request_id (202 Accepted)
 * 2. Poll GET /status/{request_id} - Check status until complete
 * 3. Return final result when status is 'complete'
 *
 * Fallback Feature:
 * - If useMockFallback is enabled and response takes longer than mockFallbackTimeout,
 *   the service will return mock data instead of continuing to wait.
 */

import { getConfig } from '../config/env';
import { getMockStatusResponse } from '../data/mockResponse';

export interface AsyncInvokeRequest {
    prompt: string;
    session_id?: string;
}

export interface AsyncInvokeResponse {
    status: 'accepted';
    request_id: string;
    message: string;
    poll_url: string;
}

export interface StatusResponse {
    request_id: string;
    status: 'processing' | 'complete' | 'error';
    created_at: number;
    updated_at: number;
    assessment?: any;
    session_id?: string;
    execution_time_ms?: number;
    error?: string;
    error_code?: string;
}

export interface ProgressCallback {
    (elapsedSeconds: number, status: string): void;
}

// =============================================================================
// S3 Storage Request/Response Interfaces
// =============================================================================

export interface SaveDecisionRequest {
    disruption_id: string;
    session_id?: string;
    flight_number: string;
    disruption_type?: string;
    selected_solution: {
        solution_id?: number;
        title: string;
        composite_score?: number;
        [key: string]: any;
    };
    detailed_report: {
        solution?: any;
        scores?: Record<string, number>;
        recovery_plan?: any;
        passenger_impact?: any;
        financial_impact?: any;
        network_impact?: any;
        [key: string]: any;
    };
}

export interface SubmitOverrideRequest {
    disruption_id: string;
    session_id?: string;
    flight_number?: string;
    disruption_type?: string;
    override_text: string;
    rejected_solutions?: Array<{
        solution_id: number;
        title: string;
        composite_score?: number;
    }>;
    context?: {
        operator_notes?: string;
        [key: string]: any;
    };
}

export interface S3StorageResponse {
    status: 'success' | 'error' | 'partial_success';
    message: string;
    s3_key?: string;
    stored_to_buckets?: Record<string, boolean>;
}

export class AsyncAPIService {
    private endpoint: string;
    private pollInterval: number = 2000; // Poll every 2 seconds
    private maxPollTime: number = 600000; // Max 10 minutes
    private mockFallbackTimeout: number; // Timeout before falling back to mock
    private useMockFallback: boolean; // Whether to use mock fallback

    constructor(endpoint?: string) {
        const config = getConfig();
        this.endpoint = endpoint || config.apiEndpoint;
        this.mockFallbackTimeout = config.mockFallbackTimeout;
        this.useMockFallback = config.useMockFallback;
    }

    /**
     * Set mock fallback timeout (in milliseconds)
     * Useful for runtime configuration
     */
    setMockFallbackTimeout(timeoutMs: number): void {
        this.mockFallbackTimeout = timeoutMs;
    }

    /**
     * Enable or disable mock fallback
     */
    setUseMockFallback(enabled: boolean): void {
        this.useMockFallback = enabled;
    }

    /**
     * Get current mock fallback timeout
     */
    getMockFallbackTimeout(): number {
        return this.mockFallbackTimeout;
    }

    /**
     * Check if mock fallback is enabled
     */
    isMockFallbackEnabled(): boolean {
        return this.useMockFallback;
    }

    /**
     * Invoke with polling - main entry point
     *
     * @param request - Invoke request with prompt
     * @param onProgress - Optional callback for progress updates
     * @returns Final assessment when complete
     */
    async invokeWithPolling(
        request: AsyncInvokeRequest,
        onProgress?: ProgressCallback
    ): Promise<StatusResponse> {
        // If mock mode is enabled globally, return mock data immediately
        if (getConfig().enableMock) {
            console.log('[AsyncAPIService] Mock mode enabled, returning mock data immediately');
            if (onProgress) {
                onProgress(0, 'mock');
            }
            return getMockStatusResponse();
        }

        // Step 1: Start async processing
        const asyncResponse = await this.startAsync(request);

        // Step 2: Poll for completion
        const startTime = Date.now();
        let elapsedSeconds = 0;
        let mockFallbackTriggered = false;

        while (true) {
            // Check if we've exceeded max poll time
            const elapsed = Date.now() - startTime;
            if (elapsed > this.maxPollTime) {
                throw new Error('Request timed out after 10 minutes');
            }

            // Check if mock fallback should be triggered
            if (this.useMockFallback && !mockFallbackTriggered && elapsed > this.mockFallbackTimeout) {
                console.log(`[AsyncAPIService] Mock fallback triggered after ${Math.floor(elapsed / 1000)}s (timeout: ${this.mockFallbackTimeout / 1000}s)`);
                mockFallbackTriggered = true;

                // Update progress to indicate fallback
                if (onProgress) {
                    onProgress(elapsedSeconds, 'fallback');
                }

                // Return mock data
                const mockResponse = getMockStatusResponse();
                mockResponse.request_id = asyncResponse.request_id; // Keep original request_id for tracking
                return mockResponse;
            }

            // Update progress
            elapsedSeconds = Math.floor(elapsed / 1000);
            if (onProgress) {
                onProgress(elapsedSeconds, 'processing');
            }

            // Check status
            const status = await this.checkStatus(asyncResponse.request_id);

            // If complete or error, return
            if (status.status === 'complete' || status.status === 'error') {
                return status;
            }

            // Wait before next poll
            await this.sleep(this.pollInterval);
        }
    }

    /**
     * Start async processing
     * 
     * @param request - Invoke request
     * @returns Async response with request_id
     */
    private async startAsync(request: AsyncInvokeRequest): Promise<AsyncInvokeResponse> {
        const url = `${this.endpoint}/invoke`;

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(request),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(
                errorData.error || `Failed to start processing: ${response.statusText}`
            );
        }

        const data: AsyncInvokeResponse = await response.json();
        return data;
    }

    /**
     * Check status of async request
     * 
     * @param requestId - Request ID to check
     * @returns Current status
     */
    private async checkStatus(requestId: string): Promise<StatusResponse> {
        const url = `${this.endpoint}/status/${requestId}`;

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(
                errorData.error || `Failed to check status: ${response.statusText}`
            );
        }

        const data: StatusResponse = await response.json();
        return data;
    }

    /**
     * Sleep utility
     */
    private sleep(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // =========================================================================
    // S3 Storage Methods
    // =========================================================================

    /**
     * Save agent decision with detailed report to S3.
     *
     * Called when:
     * 1. User selects a solution
     * 2. Recovery plan is executed
     * 3. Decision is finalized
     *
     * @param request - Save decision request with solution and report data
     * @returns Storage response with S3 key
     */
    async saveDecision(request: SaveDecisionRequest): Promise<S3StorageResponse> {
        const url = `${this.endpoint}/save-decision`;

        try {
            console.log('[AsyncAPIService] Saving decision to S3:', {
                disruption_id: request.disruption_id,
                flight_number: request.flight_number,
                solution_title: request.selected_solution?.title
            });

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(request),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.error('[AsyncAPIService] Failed to save decision:', errorData);
                return {
                    status: 'error',
                    message: errorData.message || `Failed to save decision: ${response.statusText}`
                };
            }

            const data: S3StorageResponse = await response.json();
            console.log('[AsyncAPIService] Decision saved successfully:', data.s3_key);
            return data;

        } catch (error) {
            console.error('[AsyncAPIService] Error saving decision:', error);
            return {
                status: 'error',
                message: error instanceof Error ? error.message : 'Unknown error saving decision'
            };
        }
    }

    /**
     * Submit human override directive to S3.
     *
     * Called when user rejects AI solutions and provides manual directive.
     *
     * @param request - Override submission request with directive text
     * @returns Storage response with S3 key
     */
    async submitOverride(request: SubmitOverrideRequest): Promise<S3StorageResponse> {
        const url = `${this.endpoint}/submit-override`;

        try {
            console.log('[AsyncAPIService] Submitting override to S3:', {
                disruption_id: request.disruption_id,
                override_text_preview: request.override_text?.substring(0, 50) + '...'
            });

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(request),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.error('[AsyncAPIService] Failed to submit override:', errorData);
                return {
                    status: 'error',
                    message: errorData.message || `Failed to submit override: ${response.statusText}`
                };
            }

            const data: S3StorageResponse = await response.json();
            console.log('[AsyncAPIService] Override saved successfully:', data.s3_key);
            return data;

        } catch (error) {
            console.error('[AsyncAPIService] Error submitting override:', error);
            return {
                status: 'error',
                message: error instanceof Error ? error.message : 'Unknown error submitting override'
            };
        }
    }
}

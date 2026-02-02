/**
 * Async API Service with Polling
 * 
 * Handles async invocation with polling to avoid API Gateway timeouts.
 * The flow:
 * 1. POST /invoke - Returns immediately with request_id (202 Accepted)
 * 2. Poll GET /status/{request_id} - Check status until complete
 * 3. Return final result when status is 'complete'
 */

import { getConfig } from '../config/env';

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

export class AsyncAPIService {
    private endpoint: string;
    private pollInterval: number = 2000; // Poll every 2 seconds
    private maxPollTime: number = 600000; // Max 10 minutes

    constructor(endpoint?: string) {
        this.endpoint = endpoint || getConfig().apiEndpoint;
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
        // Step 1: Start async processing
        const asyncResponse = await this.startAsync(request);

        // Step 2: Poll for completion
        const startTime = Date.now();
        let elapsedSeconds = 0;

        while (true) {
            // Check if we've exceeded max poll time
            const elapsed = Date.now() - startTime;
            if (elapsed > this.maxPollTime) {
                throw new Error('Request timed out after 10 minutes');
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
}

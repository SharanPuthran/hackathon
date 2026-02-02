/**
 * API Service Module
 * 
 * Centralized API communication with authentication and error handling
 * for the SkyMarshal AgentCore REST API.
 */

import { AWSSignatureV4, AWSCredentials } from './auth';

export interface APIConfig {
    endpoint: string;
    region: string;
    credentials?: AWSCredentials;
    timeout?: number; // Timeout in milliseconds (default: 120000ms = 2 minutes)
}

export interface InvokeRequest {
    prompt: string;
    session_id?: string;
}

export interface InvokeResponse {
    status: 'success' | 'error';
    request_id: string;
    session_id: string;
    execution_time_ms: number;
    timestamp: string;
    assessment?: Assessment;
    chunks?: any[];
    error?: string;
}

export interface Assessment {
    safety_phase: PhaseResult;
    business_phase: PhaseResult;
    final_decision: string;
    recommendations: Recommendation[];
}

export interface PhaseResult {
    agents: Record<string, AgentResult>;
    phase_status: string;
    constraints: string[];
}

export interface AgentResult {
    agent_name: string;
    status: string;
    safety_analysis?: string;
    business_impact?: string;
    confidence: number;
    reasoning: string;
}

export interface Recommendation {
    id: string;
    title: string;
    description: string;
    impact: 'low' | 'medium' | 'high';
    cost: string;
    recommended: boolean;
}

export interface HealthResponse {
    status: 'healthy' | 'degraded' | 'unhealthy';
    version: string;
    timestamp: string;
    dependencies: Record<string, string>;
}

export enum APIErrorType {
    NETWORK_ERROR = 'NETWORK_ERROR',
    AUTH_ERROR = 'AUTH_ERROR',
    TIMEOUT_ERROR = 'TIMEOUT_ERROR',
    RATE_LIMIT_ERROR = 'RATE_LIMIT_ERROR',
    VALIDATION_ERROR = 'VALIDATION_ERROR',
    SERVER_ERROR = 'SERVER_ERROR',
    UNKNOWN_ERROR = 'UNKNOWN_ERROR',
}

export interface APIError {
    type: APIErrorType;
    message: string;
    statusCode?: number;
    retryable: boolean;
    details?: any;
}

/**
 * API Service for SkyMarshal AgentCore REST API
 */
export class APIService {
    private config: APIConfig;
    private defaultTimeout: number = 120000; // 2 minutes default timeout

    constructor(config: APIConfig) {
        this.config = {
            ...config,
            timeout: config.timeout || this.defaultTimeout,
        };
    }

    /**
     * Invoke the AgentCore Runtime agent with a disruption prompt
     */
    async invoke(request: InvokeRequest): Promise<InvokeResponse> {
        const url = `${this.config.endpoint}/invoke`;
        const body = JSON.stringify(request);

        try {
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            };

            // Sign request if credentials are available
            if (this.config.credentials) {
                const signedHeaders = AWSSignatureV4.sign({
                    method: 'POST',
                    url,
                    headers,
                    body,
                    credentials: this.config.credentials,
                    region: this.config.region,
                    service: 'execute-api',
                });

                Object.assign(headers, signedHeaders);
            }

            // Create abort controller for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers,
                    body,
                    signal: controller.signal,
                });

                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw await this.handleHttpError(response);
                }

                const data: InvokeResponse = await response.json();
                return data;
            } catch (error) {
                clearTimeout(timeoutId);

                // Handle abort error as timeout
                if (error instanceof Error && error.name === 'AbortError') {
                    throw {
                        type: APIErrorType.TIMEOUT_ERROR,
                        message: `Request timed out after ${this.config.timeout! / 1000} seconds. The agent analysis is taking longer than expected.`,
                        retryable: true,
                    } as APIError;
                }

                throw error;
            }
        } catch (error) {
            throw this.handleError(error);
        }
    }

    /**
     * Check API health status
     */
    async healthCheck(): Promise<HealthResponse> {
        const url = `${this.config.endpoint}/health`;

        try {
            const response = await fetch(url, {
                method: 'GET',
            });

            if (!response.ok) {
                throw await this.handleHttpError(response);
            }

            const data: HealthResponse = await response.json();
            return data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    /**
     * Invoke with streaming support using Server-Sent Events
     * 
     * @param request - Invoke request
     * @param onChunk - Callback for each chunk received
     * @param onComplete - Callback when streaming completes
     * @param onError - Callback for errors
     */
    async invokeStreaming(
        request: InvokeRequest,
        onChunk: (chunk: any) => void,
        onComplete: (response: InvokeResponse) => void,
        onError: (error: APIError) => void
    ): Promise<void> {
        const url = `${this.config.endpoint}`;
        const body = JSON.stringify(request);

        try {
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream',
            };

            // Sign request if credentials are available
            if (this.config.credentials) {
                const signedHeaders = AWSSignatureV4.sign({
                    method: 'POST',
                    url,
                    headers,
                    body,
                    credentials: this.config.credentials,
                    region: this.config.region,
                    service: 'lambda',
                });

                Object.assign(headers, signedHeaders);
            }

            const response = await fetch(url, {
                method: 'POST',
                headers,
                body,
            });

            if (!response.ok) {
                throw await this.handleHttpError(response);
            }

            // Handle streaming response
            const reader = response.body?.getReader();
            if (!reader) {
                throw new Error('Response body is not readable');
            }

            const decoder = new TextDecoder();
            let buffer = '';
            let metadata: any = null;
            const chunks: any[] = [];

            while (true) {
                const { done, value } = await reader.read();

                if (done) break;

                // Decode chunk and add to buffer
                buffer += decoder.decode(value, { stream: true });

                // Process complete SSE messages
                const lines = buffer.split('\n\n');
                buffer = lines.pop() || ''; // Keep incomplete message in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.substring(6));

                        if (data.type === 'metadata') {
                            metadata = data;
                        } else if (data.type === 'chunk') {
                            chunks.push(data.data);
                            onChunk(data.data);
                        } else if (data.type === 'complete') {
                            // Build complete response
                            const completeResponse: InvokeResponse = {
                                status: 'success',
                                request_id: metadata?.request_id || '',
                                session_id: metadata?.session_id || '',
                                execution_time_ms: data.execution_time_ms,
                                timestamp: new Date().toISOString(),
                                assessment: this.aggregateChunks(chunks),
                            };
                            onComplete(completeResponse);
                        } else if (data.type === 'error') {
                            onError({
                                type: APIErrorType.SERVER_ERROR,
                                message: data.error_message,
                                retryable: false,
                            });
                        }
                    }
                }
            }
        } catch (error) {
            onError(this.handleError(error));
        }
    }

    /**
     * Aggregate streaming chunks into a complete assessment
     */
    private aggregateChunks(chunks: any[]): Assessment | undefined {
        if (chunks.length === 0) return undefined;

        // The last chunk typically contains the complete assessment
        const lastChunk = chunks[chunks.length - 1];

        if (lastChunk && typeof lastChunk === 'object') {
            return lastChunk as Assessment;
        }

        return undefined;
    }

    /**
     * Handle HTTP error responses
     */
    private async handleHttpError(response: Response): Promise<APIError> {
        const statusCode = response.status;
        let errorData: any = {};

        try {
            errorData = await response.json();
        } catch {
            // Response body is not JSON
        }

        switch (statusCode) {
            case 401:
                return {
                    type: APIErrorType.AUTH_ERROR,
                    message: 'Authentication failed - please check AWS credentials',
                    statusCode,
                    retryable: false,
                    details: errorData,
                };

            case 429:
                return {
                    type: APIErrorType.RATE_LIMIT_ERROR,
                    message: 'Too many requests - please wait and try again',
                    statusCode,
                    retryable: true,
                    details: errorData,
                };

            case 504:
                return {
                    type: APIErrorType.TIMEOUT_ERROR,
                    message: 'Analysis is taking longer than expected. This is normal for the first request. Retrying automatically...',
                    statusCode,
                    retryable: true,
                    details: errorData,
                };

            case 400:
                return {
                    type: APIErrorType.VALIDATION_ERROR,
                    message: errorData.error_message || 'Invalid request - please check your input',
                    statusCode,
                    retryable: false,
                    details: errorData,
                };

            case 500:
            case 502:
            case 503:
                return {
                    type: APIErrorType.SERVER_ERROR,
                    message: 'Service temporarily unavailable - please try again',
                    statusCode,
                    retryable: true,
                    details: errorData,
                };

            default:
                return {
                    type: APIErrorType.UNKNOWN_ERROR,
                    message: errorData.error_message || `HTTP ${statusCode}: ${response.statusText}`,
                    statusCode,
                    retryable: false,
                    details: errorData,
                };
        }
    }

    /**
     * Handle general errors (network, parsing, etc.)
     */
    private handleError(error: any): APIError {
        // If it's already an APIError, return it
        if (error.type && Object.values(APIErrorType).includes(error.type)) {
            return error as APIError;
        }

        // Network error
        if (error instanceof TypeError && error.message.includes('fetch')) {
            return {
                type: APIErrorType.NETWORK_ERROR,
                message: 'Unable to connect to API - please check your network connection',
                retryable: true,
                details: error,
            };
        }

        // Unknown error
        return {
            type: APIErrorType.UNKNOWN_ERROR,
            message: error.message || 'An unexpected error occurred',
            retryable: false,
            details: error,
        };
    }
}

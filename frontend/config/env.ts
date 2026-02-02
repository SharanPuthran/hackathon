/**
 * Environment Configuration Module
 * 
 * Loads and validates environment variables for the SkyMarshal frontend.
 * All configuration is loaded from Vite environment variables (VITE_* prefix).
 */

export interface EnvironmentConfig {
    apiEndpoint: string;
    awsRegion: string;
    apiTimeout: number;
    isDevelopment: boolean;
    enableMock: boolean;
}

/**
 * Validates that a URL is a valid HTTPS URL or a relative URL (for development proxy)
 */
export function isValidHttpsUrl(url: string): boolean {
    // Allow relative URLs for development proxy
    if (url.startsWith('/')) {
        return true;
    }

    try {
        const parsed = new URL(url);
        return parsed.protocol === 'https:';
    } catch {
        return false;
    }
}

/**
 * Validates the environment configuration
 * Throws an error if required variables are missing or invalid
 */
export function validateConfig(config: Partial<EnvironmentConfig>): void {
    if (!config.apiEndpoint) {
        throw new Error(
            'API endpoint is not configured. Please set VITE_API_ENDPOINT in your .env file.'
        );
    }

    if (!isValidHttpsUrl(config.apiEndpoint)) {
        throw new Error(
            `API endpoint must be a valid HTTPS URL or relative path. Got: ${config.apiEndpoint}`
        );
    }

    if (!config.awsRegion) {
        throw new Error(
            'AWS region is not configured. Please set VITE_AWS_REGION in your .env file.'
        );
    }
}

/**
 * Loads environment configuration from Vite environment variables
 * 
 * Required variables:
 * - VITE_API_ENDPOINT: The API Gateway endpoint URL (or relative path for dev proxy)
 * - VITE_AWS_REGION: The AWS region (defaults to us-east-1)
 * 
 * Optional variables:
 * - VITE_API_TIMEOUT: API request timeout in seconds (defaults to 120)
 * - VITE_ENABLE_MOCK: Enable mock mode for testing (defaults to false)
 */
export function loadConfig(): EnvironmentConfig {
    const timeoutSeconds = import.meta.env.VITE_API_TIMEOUT
        ? parseInt(import.meta.env.VITE_API_TIMEOUT, 10)
        : 120;

    const config: Partial<EnvironmentConfig> = {
        apiEndpoint: import.meta.env.VITE_API_ENDPOINT,
        awsRegion: import.meta.env.VITE_AWS_REGION || 'us-east-1',
        apiTimeout: timeoutSeconds * 1000, // Convert to milliseconds
        isDevelopment: import.meta.env.DEV === true,
        enableMock: import.meta.env.VITE_ENABLE_MOCK === 'true',
    };

    // Validate configuration
    validateConfig(config);

    return config as EnvironmentConfig;
}

/**
 * Get the current environment configuration
 * This is a singleton that loads the config once and caches it
 */
let cachedConfig: EnvironmentConfig | null = null;

export function getConfig(): EnvironmentConfig {
    if (!cachedConfig) {
        cachedConfig = loadConfig();
    }
    return cachedConfig;
}

/**
 * Reset the cached configuration (useful for testing)
 */
export function resetConfig(): void {
    cachedConfig = null;
}

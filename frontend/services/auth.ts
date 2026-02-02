/**
 * AWS Signature V4 Authentication Module
 * 
 * Implements AWS Signature Version 4 signing for API Gateway requests.
 * This is required for IAM-authenticated API Gateway endpoints.
 * 
 * Reference: https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html
 */

import CryptoJS from 'crypto-js';

export interface AWSCredentials {
    accessKeyId: string;
    secretAccessKey: string;
    sessionToken?: string;
}

export interface SignatureParams {
    method: string;
    url: string;
    headers: Record<string, string>;
    body: string;
    credentials: AWSCredentials;
    region: string;
    service: string;
}

/**
 * AWS Signature V4 implementation
 */
export class AWSSignatureV4 {
    /**
     * Sign an HTTP request with AWS Signature V4
     * Returns headers to add to the request
     */
    static sign(params: SignatureParams): Record<string, string> {
        const { method, url, headers, body, credentials, region, service } = params;

        // Parse URL
        const urlObj = new URL(url);
        const host = urlObj.host;
        const path = urlObj.pathname;
        const queryString = urlObj.search.slice(1); // Remove leading '?'

        // Create timestamp
        const now = new Date();
        const amzDate = this.getAmzDate(now);
        const dateStamp = this.getDateStamp(now);

        // Create canonical request
        const payloadHash = this.sha256(body);

        const canonicalHeaders = {
            ...headers,
            'host': host,
            'x-amz-date': amzDate,
        };

        // Add session token if present
        if (credentials.sessionToken) {
            canonicalHeaders['x-amz-security-token'] = credentials.sessionToken;
        }

        const canonicalRequest = this.createCanonicalRequest(
            method,
            path,
            queryString,
            canonicalHeaders,
            payloadHash
        );

        // Create string to sign
        const credentialScope = `${dateStamp}/${region}/${service}/aws4_request`;
        const canonicalRequestHash = this.sha256(canonicalRequest);
        const stringToSign = this.createStringToSign(amzDate, credentialScope, canonicalRequestHash);

        // Calculate signature
        const signingKey = this.getSignatureKey(
            credentials.secretAccessKey,
            dateStamp,
            region,
            service
        );
        const signature = this.hmacSha256Hex(signingKey, stringToSign);

        // Create authorization header
        const signedHeaders = Object.keys(canonicalHeaders).sort().join(';');
        const authorizationHeader =
            `AWS4-HMAC-SHA256 Credential=${credentials.accessKeyId}/${credentialScope}, ` +
            `SignedHeaders=${signedHeaders}, ` +
            `Signature=${signature}`;

        // Return headers to add to request
        const resultHeaders: Record<string, string> = {
            'Authorization': authorizationHeader,
            'X-Amz-Date': amzDate,
        };

        if (credentials.sessionToken) {
            resultHeaders['X-Amz-Security-Token'] = credentials.sessionToken;
        }

        return resultHeaders;
    }

    /**
     * Create canonical request string
     */
    private static createCanonicalRequest(
        method: string,
        uri: string,
        queryString: string,
        headers: Record<string, string>,
        payloadHash: string
    ): string {
        // Sort headers by lowercase key
        const sortedHeaders = Object.keys(headers)
            .map(key => key.toLowerCase())
            .sort();

        const canonicalHeaders = sortedHeaders
            .map(key => `${key}:${headers[key]}\n`)
            .join('');

        const signedHeaders = sortedHeaders.join(';');

        return [
            method,
            uri,
            queryString,
            canonicalHeaders,
            signedHeaders,
            payloadHash,
        ].join('\n');
    }

    /**
     * Create string to sign
     */
    private static createStringToSign(
        timestamp: string,
        credentialScope: string,
        canonicalRequestHash: string
    ): string {
        return [
            'AWS4-HMAC-SHA256',
            timestamp,
            credentialScope,
            canonicalRequestHash,
        ].join('\n');
    }

    /**
     * Derive signing key
     */
    private static getSignatureKey(
        key: string,
        dateStamp: string,
        region: string,
        service: string
    ): CryptoJS.lib.WordArray {
        const kDate = this.hmacSha256(`AWS4${key}`, dateStamp);
        const kRegion = this.hmacSha256(kDate, region);
        const kService = this.hmacSha256(kRegion, service);
        const kSigning = this.hmacSha256(kService, 'aws4_request');
        return kSigning;
    }

    /**
     * Get AMZ date format (YYYYMMDDTHHMMSSZ)
     */
    private static getAmzDate(date: Date): string {
        return date.toISOString().replace(/[:-]|\.\d{3}/g, '');
    }

    /**
     * Get date stamp format (YYYYMMDD)
     */
    private static getDateStamp(date: Date): string {
        return date.toISOString().slice(0, 10).replace(/-/g, '');
    }

    /**
     * SHA256 hash (hex output)
     */
    private static sha256(data: string): string {
        return CryptoJS.SHA256(data).toString(CryptoJS.enc.Hex);
    }

    /**
     * HMAC SHA256 (WordArray output)
     */
    private static hmacSha256(key: string | CryptoJS.lib.WordArray, data: string): CryptoJS.lib.WordArray {
        if (typeof key === 'string') {
            return CryptoJS.HmacSHA256(data, key);
        }
        return CryptoJS.HmacSHA256(data, key);
    }

    /**
     * HMAC SHA256 (hex output)
     */
    private static hmacSha256Hex(key: CryptoJS.lib.WordArray, data: string): string {
        return CryptoJS.HmacSHA256(data, key).toString(CryptoJS.enc.Hex);
    }
}

/**
 * Get AWS credentials from environment or AWS SDK
 * 
 * Note: In a browser environment, credentials should be obtained through:
 * 1. Cognito Identity Pool
 * 2. Temporary credentials from a backend service
 * 3. AWS Amplify
 * 
 * For development, credentials can be passed directly, but this is NOT recommended for production.
 */
export async function getAWSCredentials(): Promise<AWSCredentials | null> {
    // TODO: Implement proper credential retrieval
    // Options:
    // 1. Use AWS Amplify: Auth.currentCredentials()
    // 2. Use Cognito Identity Pool
    // 3. Fetch temporary credentials from backend

    // For now, return null to indicate credentials are not available
    // The application should handle this gracefully
    return null;
}

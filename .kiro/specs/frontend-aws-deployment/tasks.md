# Implementation Plan: Frontend AWS Deployment

## Overview

This implementation plan breaks down the deployment infrastructure into discrete, testable steps. The approach follows infrastructure-as-code principles using shell scripts and AWS CLI commands. Each task builds incrementally, with early validation through automated tests to catch configuration errors before they reach production.

## Tasks

- [x] 1. Set up deployment script structure and AWS credential verification
  - Create `deploy.sh` script in project root with proper permissions
  - Implement AWS credential check using `aws sts get-caller-identity`
  - Add environment variable validation for required VITE\_\* variables
  - Implement logging functions for deployment steps
  - _Requirements: 9.1, 9.2, 9.4_

- [ ]\* 1.1 Write property test for AWS credential validation
  - **Property 17: AWS Credential Validation**
  - **Validates: Requirements 9.2**

- [x] 2. Implement Vite build configuration and verification
  - Update `frontend/vite.config.ts` to properly handle environment variables
  - Configure build output settings (minification, source maps, chunking)
  - Add build verification function to check dist/ directory contents
  - Implement content hash verification for generated assets
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ]\* 2.1 Write property test for TypeScript compilation
  - **Property 1: TypeScript Compilation Completeness**
  - **Validates: Requirements 1.1**

- [ ]\* 2.2 Write property test for build output location
  - **Property 2: Build Output Location**
  - **Validates: Requirements 1.2**

- [ ]\* 2.3 Write property test for minification
  - **Property 3: Production Minification**
  - **Validates: Requirements 1.3**

- [ ]\* 2.4 Write property test for content hash generation
  - **Property 4: Content Hash Generation**
  - **Validates: Requirements 1.4**

- [x] 3. Create S3 bucket with static website hosting configuration
  - Implement function to create S3 bucket with unique name (skymarshal-frontend-368613657554)
  - Configure static website hosting with index.html as index and error document
  - Add idempotency check to skip creation if bucket already exists
  - Implement bucket verification to confirm correct region and configuration
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ]\* 3.1 Write property test for bucket configuration
  - **Property 8: S3 Bucket Configuration**
  - **Validates: Requirements 2.2, 2.3, 2.4**

- [ ]\* 3.2 Write property test for bucket naming compliance
  - **Property 9: Bucket Naming Compliance**
  - **Validates: Requirements 2.5**

- [x] 4. Configure S3 bucket policies and public access blocking
  - Enable S3 public access block settings on the bucket
  - Create Origin Access Identity (OAI) for CloudFront
  - Generate and apply bucket policy allowing OAI read access
  - Verify direct S3 access is blocked (returns 403)
  - _Requirements: 3.1, 3.2, 3.4, 3.5_

- [ ]\* 4.1 Write property test for OAI access policy
  - **Property 10: OAI Access Policy**
  - **Validates: Requirements 3.1**

- [ ]\* 4.2 Write property test for public access blocking
  - **Property 11: Public Access Blocking**
  - **Validates: Requirements 3.2, 3.4**

- [x] 5. Implement file upload with proper metadata and headers
  - Create Content-Type mapping for common file extensions (.html, .js, .css, .json, .png, .svg, .ico)
  - Implement Cache-Control strategy: no-cache for HTML, max-age=31536000 for hashed assets, max-age=86400 for others
  - Write upload function using `aws s3 sync` with metadata flags
  - Verify all files from dist/ are uploaded with correct S3 keys
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 8.4_

- [ ]\* 5.1 Write property test for complete file upload
  - **Property 13: Complete File Upload**
  - **Validates: Requirements 4.1, 4.4**

- [ ]\* 5.2 Write property test for Content-Type correctness
  - **Property 14: Content-Type Correctness**
  - **Validates: Requirements 4.2**

- [ ]\* 5.3 Write property test for Cache-Control headers
  - **Property 15: Cache-Control Headers**
  - **Validates: Requirements 4.3, 8.1, 8.2, 8.4**

- [x] 6. Create CloudFront distribution with S3 origin
  - Generate CloudFront distribution configuration JSON with S3 origin
  - Set default cache behavior (redirect-to-https, compression enabled, allowed methods)
  - Configure custom error response for 404 → index.html (200 status) for SPA routing
  - Create distribution using `aws cloudfront create-distribution`
  - Store distribution ID for future operations
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.5_

- [ ]\* 6.1 Write property test for OAI configuration
  - **Property 21: Origin Access Identity Configuration**
  - **Validates: Requirements 5.2**

- [ ]\* 6.2 Write property test for compression
  - **Property 22: Compression Enabled**
  - **Validates: Requirements 5.3**

- [ ]\* 6.3 Write property test for cache behavior
  - **Property 23: Cache Behavior Compliance**
  - **Validates: Requirements 5.4, 8.5**

- [ ]\* 6.4 Write property test for distribution status
  - **Property 24: Distribution Deployment Status**
  - **Validates: Requirements 5.5**

- [x] 7. Checkpoint - Verify infrastructure is created correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement CloudFront cache invalidation
  - Create invalidation function that generates unique caller reference (timestamp)
  - Invalidate critical paths: /index.html and optionally /assets/\*
  - Wait for invalidation to complete or timeout after 5 minutes
  - Log invalidation ID and status
  - _Requirements: 4.5_

- [ ]\* 8.1 Write property test for post-deployment invalidation
  - **Property 16: Post-Deployment Invalidation**
  - **Validates: Requirements 4.5**

- [x] 9. Add deployment verification and health checks
  - Implement function to wait for CloudFront distribution to reach "Deployed" status
  - Make test HTTP request to CloudFront distribution URL
  - Verify response status is 200 and content includes expected HTML
  - Test SPA routing by requesting a non-root path (e.g., /dashboard)
  - Verify direct S3 access returns 403
  - _Requirements: 3.3, 9.5_

- [ ]\* 9.1 Write property test for CloudFront access success
  - **Property 12: CloudFront Access Success**
  - **Validates: Requirements 3.3**

- [ ]\* 9.2 Write property test for deployment verification
  - **Property 19: Deployment Verification**
  - **Validates: Requirements 9.5**

- [ ]\* 9.3 Write property test for non-root path handling
  - **Property 25: Non-Root Path Handling**
  - **Validates: Requirements 6.1, 6.2**

- [ ]\* 9.4 Write property test for URL preservation
  - **Property 26: URL Preservation**
  - **Validates: Requirements 6.3**

- [ ]\* 9.5 Write property test for static asset 404 handling
  - **Property 27: Static Asset 404 Handling**
  - **Validates: Requirements 6.5**

- [x] 10. Implement error handling and recovery
  - Add try-catch blocks for all AWS CLI commands
  - Implement specific error handlers for common failures (auth, bucket exists, upload failure)
  - Add rollback capability for failed deployments
  - Ensure all error messages include context and recovery suggestions
  - _Requirements: 9.3_

- [ ]\* 10.1 Write property test for error message clarity
  - **Property 18: Deployment Logging**
  - **Validates: Requirements 9.4**

- [x] 11. Add idempotency and configuration management
  - Implement checks to skip resource creation if already exists
  - Create configuration file (deploy-config.json) for deployment settings
  - Store bucket name, distribution ID, and region in configuration
  - Verify running deployment twice produces same result without errors
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ]\* 11.1 Write property test for idempotent deployment
  - **Property 20: Idempotent Deployment**
  - **Validates: Requirements 10.4**

- [ ]\* 11.2 Write property test for configuration completeness
  - **Property 28: Configuration File Completeness**
  - **Validates: Requirements 10.2, 10.3**

- [x] 12. Create environment variable documentation and validation
  - Create .env.example file with all required VITE\_\* variables
  - Add comments explaining each variable's purpose
  - Update .gitignore to exclude .env files
  - Implement validation function to check required variables before build
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ]\* 12.1 Write property test for environment variable embedding
  - **Property 6: Environment Variable Embedding**
  - **Validates: Requirements 7.1, 7.2**

- [ ]\* 12.2 Write property test for missing variable handling
  - **Property 7: Missing Environment Variable Handling**
  - **Validates: Requirements 7.4**

- [x] 13. Create deployment documentation and usage guide
  - Write README section explaining deployment process
  - Document prerequisites (AWS SSO, Node.js, npm)
  - Provide step-by-step deployment instructions
  - Document troubleshooting common issues
  - Include examples of deployment commands for different environments
  - _Requirements: 7.5, 9.1_

- [x] 14. Final checkpoint - Complete deployment test
  - Run full deployment from clean state
  - Verify all infrastructure is created correctly
  - Test application functionality through CloudFront URL
  - Verify SPA routing works for multiple paths
  - Confirm cache invalidation works
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The deployment script should be idempotent and safe to run multiple times
- AWS credentials must be configured via AWS SSO before deployment
- Environment variables must be set in .env file before building

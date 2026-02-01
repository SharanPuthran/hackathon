# Design Document: Frontend AWS Deployment

## Overview

This design specifies the architecture and implementation approach for deploying the SkyMarshal React frontend to AWS using S3 for static hosting and CloudFront for global content delivery. The deployment follows infrastructure-as-code principles using AWS CLI and shell scripts for automation, with support for single-page application routing patterns and secure environment variable handling.

The deployment consists of three main components:

1. **Build Pipeline**: Vite-based production build with environment variable injection
2. **Storage Layer**: S3 bucket configured for static website hosting with appropriate policies
3. **Distribution Layer**: CloudFront CDN with Origin Access Identity for secure, low-latency global delivery

## Architecture

### High-Level Architecture

```
┌─────────────────┐
│   Developer     │
│   Workstation   │
└────────┬────────┘
         │
         │ npm run build
         │ deploy script
         ▼
┌─────────────────┐
│  Vite Build     │
│  System         │
│  (dist/)        │
└────────┬────────┘
         │
         │ AWS CLI upload
         ▼
┌─────────────────┐      ┌──────────────────┐
│   S3 Bucket     │◄─────│  Origin Access   │
│   (Private)     │      │  Identity (OAI)  │
│                 │      └────────┬─────────┘
│ - index.html    │               │
│ - assets/       │               │
│ - *.js, *.css   │               │
└─────────────────┘               │
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   CloudFront    │
                         │   Distribution  │
                         │                 │
                         │ - Global CDN    │
                         │ - HTTPS         │
                         │ - Compression   │
                         └────────┬────────┘
                                  │
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │  Edge    │  │  Edge    │  │  Edge    │
              │ Location │  │ Location │  │ Location │
              │  (US)    │  │  (EU)    │  │  (APAC)  │
              └────┬─────┘  └────┬─────┘  └────┬─────┘
                   │             │             │
                   ▼             ▼             ▼
              End Users    End Users    End Users
```

### Component Interaction Flow

1. **Build Phase**:
   - Developer runs `npm run build` with environment variables
   - Vite compiles TypeScript, bundles dependencies, optimizes assets
   - Output written to `dist/` directory with content-hashed filenames

2. **Upload Phase**:
   - Deployment script authenticates with AWS SSO
   - Script uploads all files from `dist/` to S3 bucket
   - Content-Type and Cache-Control headers set per file type
   - CloudFront cache invalidation triggered

3. **Request Phase**:
   - User requests URL (e.g., `https://d123.cloudfront.net/dashboard`)
   - CloudFront checks edge location cache
   - If cache miss, CloudFront requests from S3 via OAI
   - For non-existent paths, custom error response returns `index.html`
   - React app loads and handles client-side routing

## Components and Interfaces

### 1. Build System (Vite)

**Configuration**: `frontend/vite.config.ts`

```typescript
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom"],
        },
      },
    },
  },
  define: {
    "import.meta.env.VITE_GEMINI_API_KEY": JSON.stringify(
      process.env.VITE_GEMINI_API_KEY,
    ),
  },
});
```

**Environment Variables**:

- `VITE_GEMINI_API_KEY`: API key for Gemini integration
- Additional variables prefixed with `VITE_` are automatically exposed to client code

**Build Output Structure**:

```
dist/
├── index.html
├── assets/
│   ├── index-[hash].js
│   ├── index-[hash].css
│   └── vendor-[hash].js
└── favicon.ico
```

### 2. S3 Bucket Configuration

**Bucket Properties**:

- Name: `skymarshal-frontend-[account-id]` (ensures global uniqueness)
- Region: `us-east-1`
- Versioning: Disabled (not needed for static sites)
- Public Access: Blocked (access only via CloudFront)

**Static Website Hosting**:

```json
{
  "IndexDocument": {
    "Suffix": "index.html"
  },
  "ErrorDocument": {
    "Key": "index.html"
  }
}
```

**Bucket Policy** (allows CloudFront OAI access):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontOAI",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity [OAI-ID]"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::skymarshal-frontend-[account-id]/*"
    }
  ]
}
```

### 3. CloudFront Distribution

**Origin Configuration**:

```json
{
  "Id": "S3-skymarshal-frontend",
  "DomainName": "skymarshal-frontend-[account-id].s3.us-east-1.amazonaws.com",
  "S3OriginConfig": {
    "OriginAccessIdentity": "origin-access-identity/cloudfront/[OAI-ID]"
  }
}
```

**Default Cache Behavior**:

```json
{
  "TargetOriginId": "S3-skymarshal-frontend",
  "ViewerProtocolPolicy": "redirect-to-https",
  "AllowedMethods": ["GET", "HEAD", "OPTIONS"],
  "CachedMethods": ["GET", "HEAD"],
  "Compress": true,
  "DefaultTTL": 86400,
  "MaxTTL": 31536000,
  "MinTTL": 0,
  "ForwardedValues": {
    "QueryString": false,
    "Cookies": {
      "Forward": "none"
    }
  }
}
```

**Custom Error Response** (for SPA routing):

```json
{
  "ErrorCode": 404,
  "ResponsePagePath": "/index.html",
  "ResponseCode": "200",
  "ErrorCachingMinTTL": 300
}
```

### 4. Deployment Script

**Interface**: Shell script `deploy.sh`

```bash
#!/bin/bash
# Usage: ./deploy.sh [environment]
# Environment: dev | prod (default: dev)

ENVIRONMENT=${1:-dev}
BUCKET_NAME="skymarshal-frontend-368613657554"
DISTRIBUTION_ID="" # Set after CloudFront creation

# Functions:
# - build_frontend(): Run npm build
# - create_s3_bucket(): Create and configure S3 bucket
# - create_cloudfront(): Create CloudFront distribution
# - upload_to_s3(): Upload dist/ to S3 with proper headers
# - invalidate_cache(): Invalidate CloudFront cache
# - verify_deployment(): Check deployment health
```

**AWS CLI Commands Used**:

- `aws s3 mb` - Create bucket
- `aws s3 website` - Configure static hosting
- `aws s3api put-bucket-policy` - Set bucket policy
- `aws s3 sync` - Upload files with headers
- `aws cloudfront create-distribution` - Create CDN
- `aws cloudfront create-invalidation` - Clear cache
- `aws cloudfront get-distribution` - Check status

## Data Models

### Deployment Configuration

```typescript
interface DeploymentConfig {
  environment: "dev" | "prod";
  awsRegion: string;
  awsAccountId: string;
  bucketName: string;
  distributionId?: string;
  buildDir: string;
  envVars: Record<string, string>;
}
```

### S3 Upload Metadata

```typescript
interface S3UploadFile {
  localPath: string;
  s3Key: string;
  contentType: string;
  cacheControl: string;
}

// Content-Type mapping
const CONTENT_TYPES: Record<string, string> = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

// Cache-Control strategy
const CACHE_STRATEGIES = {
  html: "no-cache, no-store, must-revalidate", // Always fetch fresh
  hashed: "public, max-age=31536000, immutable", // Cache forever (content-hashed)
  static: "public, max-age=86400", // Cache for 1 day
};
```

### CloudFront Invalidation

```typescript
interface InvalidationRequest {
  distributionId: string;
  paths: string[];
  callerReference: string; // Unique ID (timestamp)
}

// Typical invalidation paths
const INVALIDATION_PATHS = [
  "/index.html",
  "/assets/*", // Only if needed for immediate updates
];
```

## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Build System Properties

**Property 1: TypeScript Compilation Completeness**
_For any_ valid TypeScript source file in the project, after running the build command, the output directory should contain a corresponding compiled JavaScript file and no TypeScript files.
**Validates: Requirements 1.1**

**Property 2: Build Output Location**
_For any_ build execution, all generated static assets should be located in the dist directory with no build artifacts outside this directory.
**Validates: Requirements 1.2**

**Property 3: Production Minification**
_For any_ JavaScript or CSS file in the production build, the file size should be significantly smaller than the source, and the content should not contain unnecessary whitespace or long variable names.
**Validates: Requirements 1.3**

**Property 4: Content Hash Generation**
_For any_ static asset file (JS, CSS), the filename should include a content hash, and changing the file content should result in a different hash in the filename.
**Validates: Requirements 1.4**

**Property 5: Dependency Bundling**
_For any_ required dependency imported in the source code, the production bundle should include that dependency's code, allowing the application to run without external module loading.
**Validates: Requirements 1.5**

**Property 6: Environment Variable Embedding**
_For any_ environment variable prefixed with VITE\_ in the .env file, the production bundle should contain the variable's value embedded in the JavaScript code.
**Validates: Requirements 7.1, 7.2**

**Property 7: Missing Environment Variable Handling**
_For any_ required environment variable that is not set, the build process should fail with an error message that includes the variable name.
**Validates: Requirements 7.4**

### S3 Infrastructure Properties

**Property 8: S3 Bucket Configuration**
_For any_ deployed S3 bucket, querying the bucket's website configuration should return index.html as both the index document and error document.
**Validates: Requirements 2.2, 2.3, 2.4**

**Property 9: Bucket Naming Compliance**
_For any_ created S3 bucket name, it should match AWS naming rules: lowercase alphanumeric characters and hyphens only, 3-63 characters long, no consecutive periods.
**Validates: Requirements 2.5**

**Property 10: OAI Access Policy**
_For any_ deployed S3 bucket, the bucket policy should grant s3:GetObject permission to the CloudFront Origin Access Identity and no other principals.
**Validates: Requirements 3.1**

**Property 11: Public Access Blocking**
_For any_ deployed S3 bucket, attempting to access an object via direct S3 URL should return a 403 Forbidden error.
**Validates: Requirements 3.2, 3.4**

**Property 12: CloudFront Access Success**
_For any_ object uploaded to the S3 bucket, requesting that object through the CloudFront distribution URL should return a 200 status code with the correct content.
**Validates: Requirements 3.3**

### Deployment Pipeline Properties

**Property 13: Complete File Upload**
_For any_ file in the dist directory after build, there should be a corresponding object in the S3 bucket with the same relative path after deployment.
**Validates: Requirements 4.1, 4.4**

**Property 14: Content-Type Correctness**
_For any_ uploaded file in S3, the Content-Type metadata should match the file extension (e.g., .js → application/javascript, .html → text/html, .css → text/css).
**Validates: Requirements 4.2**

**Property 15: Cache-Control Headers**
_For any_ uploaded file in S3, the Cache-Control metadata should be set appropriately: no-cache for HTML files, max-age=31536000 for content-hashed assets, max-age=86400 for other static files.
**Validates: Requirements 4.3, 8.1, 8.2, 8.4**

**Property 16: Post-Deployment Invalidation**
_For any_ deployment execution, after files are uploaded to S3, a CloudFront invalidation should be created for the distribution.
**Validates: Requirements 4.5**

**Property 17: AWS Credential Validation**
_For any_ deployment execution, if AWS credentials are not configured or are invalid, the deployment should fail immediately with an error message before attempting any AWS operations.
**Validates: Requirements 9.2**

**Property 18: Deployment Logging**
_For any_ deployment execution, the output should include log messages for each major step: build, bucket creation/verification, file upload, CloudFront configuration, and invalidation.
**Validates: Requirements 9.4**

**Property 19: Deployment Verification**
_For any_ deployment execution that completes without errors, the script should make a test HTTP request to the CloudFront distribution URL and verify it returns a 200 status code before exiting.
**Validates: Requirements 9.5**

**Property 20: Idempotent Deployment**
_For any_ deployment configuration, running the deployment script multiple times with the same configuration should succeed without creating duplicate resources or causing errors.
**Validates: Requirements 10.4**

### CloudFront Distribution Properties

**Property 21: Origin Access Identity Configuration**
_For any_ deployed CloudFront distribution, the origin configuration should specify an Origin Access Identity for accessing the S3 bucket.
**Validates: Requirements 5.2**

**Property 22: Compression Enabled**
_For any_ deployed CloudFront distribution, the default cache behavior should have compression enabled, and responses for text-based content should include Content-Encoding: gzip or br headers.
**Validates: Requirements 5.3**

**Property 23: Cache Behavior Compliance**
_For any_ static asset request through CloudFront, the response should include cache headers that respect the Cache-Control values set on the S3 objects.
**Validates: Requirements 5.4, 8.5**

**Property 24: Distribution Deployment Status**
_For any_ CloudFront distribution created by the deployment pipeline, querying the distribution status should return "Deployed" and the enabled flag should be true.
**Validates: Requirements 5.5**

### SPA Routing Properties

**Property 25: Non-Root Path Handling**
_For any_ valid URL path (e.g., /dashboard, /settings/profile) requested through the CloudFront distribution, the response should return the content of index.html with a 200 status code.
**Validates: Requirements 6.1, 6.2**

**Property 26: URL Preservation**
_For any_ client-side route requested through CloudFront, the URL in the browser should remain unchanged (not redirected to /index.html).
**Validates: Requirements 6.3**

**Property 27: Static Asset 404 Handling**
_For any_ non-existent static asset path (e.g., /assets/missing-file.js), the CloudFront distribution should return a 404 status code, not index.html.
**Validates: Requirements 6.5**

### Configuration Management Properties

**Property 28: Configuration File Completeness**
_For any_ infrastructure configuration file, it should specify all required S3 bucket settings (name, region, website hosting, policies) and all CloudFront distribution settings (origin, cache behaviors, error responses).
**Validates: Requirements 10.2, 10.3**

## Error Handling

### Build Errors

**Missing Dependencies**:

- Detection: Build fails with module resolution errors
- Handling: Display clear error message indicating which dependency is missing
- Recovery: User runs `npm install` to install dependencies

**TypeScript Compilation Errors**:

- Detection: Build fails with type errors
- Handling: Display TypeScript error messages with file locations and line numbers
- Recovery: User fixes type errors in source code

**Missing Environment Variables**:

- Detection: Build process checks for required VITE\_\* variables
- Handling: Fail build with error message listing missing variables
- Recovery: User creates .env file with required variables

### Deployment Errors

**AWS Authentication Failure**:

- Detection: AWS CLI commands return authentication errors
- Handling: Fail immediately with message to configure AWS SSO or credentials
- Recovery: User runs `aws sso login` or configures credentials

**S3 Bucket Already Exists**:

- Detection: Bucket creation returns BucketAlreadyExists error
- Handling: Check if bucket is in correct region and owned by account
- Recovery: If owned, continue with deployment; if not, fail with error

**S3 Upload Failure**:

- Detection: AWS CLI sync command returns non-zero exit code
- Handling: Display error message with failed file paths
- Recovery: Retry upload or check AWS permissions

**CloudFront Creation Failure**:

- Detection: CloudFront API returns error during distribution creation
- Handling: Display error message and check for existing distributions
- Recovery: User manually deletes conflicting distribution or fixes configuration

**Invalidation Failure**:

- Detection: CloudFront invalidation API returns error
- Handling: Log warning but don't fail deployment (cache will expire naturally)
- Recovery: User can manually create invalidation via AWS Console

### Runtime Errors

**404 on CloudFront**:

- Detection: User reports pages not loading
- Handling: Verify custom error response is configured correctly
- Recovery: Update CloudFront distribution with correct error response settings

**CORS Errors**:

- Detection: Browser console shows CORS errors
- Handling: Verify CloudFront allows required HTTP methods and headers
- Recovery: Update CloudFront cache behavior to allow OPTIONS method

**Stale Content**:

- Detection: Users see old version after deployment
- Handling: Verify invalidation was created and completed
- Recovery: Create manual invalidation for affected paths

## Testing Strategy

### Dual Testing Approach

This deployment system requires both unit tests and property-based tests for comprehensive validation:

- **Unit tests**: Verify specific deployment scenarios, edge cases, and error conditions
- **Property tests**: Verify universal properties across different configurations and inputs

Both testing approaches are complementary and necessary. Unit tests catch concrete bugs in specific scenarios, while property tests verify general correctness across a wide range of inputs.

### Unit Testing

Unit tests should focus on:

1. **Specific Deployment Scenarios**:
   - First-time deployment (no existing resources)
   - Update deployment (resources already exist)
   - Deployment with missing environment variables
   - Deployment with invalid AWS credentials

2. **Edge Cases**:
   - Empty dist directory
   - Very large files (>5GB)
   - Special characters in filenames
   - Deeply nested directory structures

3. **Error Conditions**:
   - Network failures during upload
   - Insufficient AWS permissions
   - Invalid CloudFront configuration
   - S3 bucket name conflicts

4. **Integration Points**:
   - Vite build integration
   - AWS CLI command execution
   - Environment variable loading
   - File system operations

### Property-Based Testing

Property-based tests should verify universal properties using a property-based testing library (e.g., Hypothesis for Python, fast-check for JavaScript/TypeScript).

**Configuration**:

- Minimum 100 iterations per property test
- Each test tagged with: **Feature: frontend-aws-deployment, Property N: [property text]**
- Use generators for: file paths, S3 keys, environment variables, HTTP headers

**Property Test Examples**:

1. **Content-Type Mapping** (Property 14):
   - Generate random file extensions
   - Verify Content-Type header matches expected MIME type
   - Tag: **Feature: frontend-aws-deployment, Property 14: Content-Type Correctness**

2. **Cache-Control Strategy** (Property 15):
   - Generate random file paths with different extensions
   - Verify Cache-Control header matches file type strategy
   - Tag: **Feature: frontend-aws-deployment, Property 15: Cache-Control Headers**

3. **Path Preservation** (Property 13):
   - Generate random directory structures
   - Verify S3 keys match local paths after upload
   - Tag: **Feature: frontend-aws-deployment, Property 13: Complete File Upload**

4. **Idempotency** (Property 20):
   - Generate random deployment configurations
   - Run deployment twice, verify no errors or duplicates
   - Tag: **Feature: frontend-aws-deployment, Property 20: Idempotent Deployment**

### Testing Tools

- **Build Testing**: Jest or Vitest for Vite build verification
- **AWS Testing**: LocalStack for local AWS service emulation
- **Property Testing**: fast-check (TypeScript) or Hypothesis (Python)
- **Integration Testing**: Playwright or Cypress for end-to-end deployment verification
- **Infrastructure Testing**: AWS CLI commands with --dry-run flag

### Test Execution

```bash
# Run all unit tests
npm test

# Run property-based tests
npm run test:properties

# Run integration tests (requires AWS credentials)
npm run test:integration

# Run all tests
npm run test:all
```

### Continuous Integration

Tests should run automatically on:

- Pull requests (unit and property tests)
- Main branch commits (all tests including integration)
- Scheduled nightly builds (full deployment test to staging)

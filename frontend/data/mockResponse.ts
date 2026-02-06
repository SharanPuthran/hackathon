/**
 * Mock Response Data
 *
 * This file loads mock data from solution JSON files when:
 * 1. API response takes longer than the configured timeout
 * 2. Mock mode is enabled via configuration
 *
 * Configuration:
 * - Set VITE_MOCK_SOLUTION environment variable to switch between solutions
 * - Available solutions: solution_1 through solution_6
 * 
 * Note: After changing VITE_MOCK_SOLUTION in .env, you must restart the dev server
 * for the changes to take effect (Vite doesn't hot-reload env variables).
 */

import { getConfig } from '../config/env';

// Define a flexible type for mock responses (allows different solution structures)
type MockResponse = Record<string, unknown>;

// Lazy-loaded solution registry - solutions are loaded on-demand
let solutionsCache: Record<string, MockResponse> | null = null;

/**
 * Load all solutions dynamically
 * This is called once and cached for performance
 */
async function loadSolutions(): Promise<Record<string, MockResponse>> {
  if (solutionsCache) {
    return solutionsCache;
  }

  // Dynamic imports for all solutions
  const [solution1, solution2, solution3, solution4, solution5, solution6] = await Promise.all([
    import('./responses/solution_1.json'),
    import('./responses/solution_2.json'),
    import('./responses/solution_3.json'),
    import('./responses/solution_4.json'),
    import('./responses/solution_5.json'),
    import('./responses/solution_6.json'),
  ]);

  solutionsCache = {
    'solution_1': solution1.default,
    'solution_2': solution2.default,
    'solution_3': solution3.default,
    'solution_4': solution4.default,
    'solution_5': solution5.default,
    'solution_6': solution6.default,
  };

  return solutionsCache;
}

/**
 * Get list of available solution keys
 */
export const getAvailableSolutions = (): string[] => [
  'solution_1',
  'solution_2',
  'solution_3',
  'solution_4',
  'solution_5',
  'solution_6'
];

/**
 * Get the currently selected mock solution based on configuration
 */
async function getSelectedSolution(): Promise<MockResponse> {
  const config = getConfig();
  const solutionKey = config.mockSolutionFile || 'solution_1';

  console.log(`[MockResponse] Loading solution: ${solutionKey}`);

  const solutions = await loadSolutions();

  if (!(solutionKey in solutions)) {
    console.warn(`Mock solution "${solutionKey}" not found, falling back to solution_1`);
    return solutions['solution_1'];
  }

  return solutions[solutionKey];
}

/**
 * Generate a mock StatusResponse that wraps the mock data
 * Calls getSelectedSolution() fresh each time to pick up config changes
 */
export async function getMockStatusResponse(): Promise<any> {
  const selectedSolution = await getSelectedSolution();

  return {
    request_id: 'mock-request-' + Date.now(),
    status: 'complete' as const,
    created_at: Date.now() - 60000,
    updated_at: Date.now(),
    execution_time_ms: 45000,
    session_id: 'mock-session-' + Date.now(),
    assessment: selectedSolution
  };
}

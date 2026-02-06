/**
 * Mock Solution Switcher Utility
 * 
 * Provides runtime control over which mock solution is loaded.
 * Useful for testing different scenarios without restarting the dev server.
 * 
 * Usage in browser console:
 * ```
 * window.switchMockSolution('solution_3')
 * ```
 */

import { resetConfig } from '../config/env';

// Store the current solution override
let solutionOverride: string | null = null;

/**
 * Get the current solution override (if any)
 */
export function getSolutionOverride(): string | null {
    return solutionOverride;
}

/**
 * Set a solution override at runtime
 * This will take effect on the next API call
 * 
 * @param solution - Solution key (e.g., 'solution_1', 'solution_2', etc.)
 */
export function setSolutionOverride(solution: string): void {
    console.log(`[MockSolutionSwitcher] Switching to ${solution}`);
    solutionOverride = solution;

    // Update the environment variable for Vite
    if (typeof window !== 'undefined') {
        // @ts-ignore - Vite injects import.meta.env
        import.meta.env.VITE_MOCK_SOLUTION = solution;
    }

    // Reset config cache to pick up new value
    resetConfig();

    console.log(`[MockSolutionSwitcher] Solution switched to ${solution}. Refresh the page or submit a new query to see changes.`);
}

/**
 * Clear the solution override
 */
export function clearSolutionOverride(): void {
    console.log('[MockSolutionSwitcher] Clearing solution override');
    solutionOverride = null;
    resetConfig();
}

/**
 * Get list of available solutions
 */
export function getAvailableSolutions(): string[] {
    return [
        'solution_1',
        'solution_2',
        'solution_3',
        'solution_4',
        'solution_5',
        'solution_6'
    ];
}

// Expose to window for easy console access
if (typeof window !== 'undefined') {
    (window as any).switchMockSolution = setSolutionOverride;
    (window as any).clearMockSolution = clearSolutionOverride;
    (window as any).getAvailableSolutions = getAvailableSolutions;

    console.log('[MockSolutionSwitcher] Available commands:');
    console.log('  window.switchMockSolution("solution_X") - Switch to a different solution');
    console.log('  window.clearMockSolution() - Clear override and use .env value');
    console.log('  window.getAvailableSolutions() - List available solutions');
}

import { useEffect } from 'react';
import useGlobalState from '@/hooks/use-global-state';
import { 
  fetchPerformanceMetrics, 
  startPerformanceMetricsAutoRefresh, 
  stopPerformanceMetricsAutoRefresh 
} from '@/lib/performance-metrics-api';

/**
 * Hook to manage automatic performance metrics updates during simulation
 */
export const usePerformanceMetrics = () => {
  const { isSimulating } = useGlobalState();

  useEffect(() => {
    let intervalId = null;

    if (isSimulating) {
      // Initial fetch
      fetchPerformanceMetrics();
      
      // Start auto-refresh every 5 seconds during simulation
      intervalId = startPerformanceMetricsAutoRefresh(5000);
    }

    // Cleanup on unmount or when simulation stops
    return () => {
      if (intervalId) {
        stopPerformanceMetricsAutoRefresh(intervalId);
      }
    };
  }, [isSimulating]);

  // Manual refresh function
  const refreshMetrics = async () => {
    return await fetchPerformanceMetrics();
  };

  return { refreshMetrics };
};
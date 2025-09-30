import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { 
  TrendingUp, 
  TrendingDown, 
  Equal, 
  Clock, 
  Zap, 
  Users, 
  Target,
  RefreshCw,
  X
} from "lucide-react";
import useGlobalState from "@/hooks/use-global-state";
import { useState, useEffect } from "react";
import { compareAlgorithms } from "@/lib/simulation-management/performance-metrics";

export default function AlgorithmComparisonPanel({ isOpen, onClose }) {
  const { algorithmComparison, assignmentAlgorithm } = useGlobalState();
  const [isLoading, setIsLoading] = useState(false);
  const [testLocation, setTestLocation] = useState({ x: 300, y: 400 });

  const handleCompare = async () => {
    setIsLoading(true);
    await compareAlgorithms(testLocation);
    setIsLoading(false);
  };

  const formatNumber = (num) => {
    if (num === 0) return "0";
    if (num < 1) return num.toFixed(3);
    if (num < 100) return num.toFixed(2);
    return Math.round(num).toLocaleString();
  };

  const formatMs = (ms) => {
    if (ms < 1000) return `${formatNumber(ms)}ms`;
    return `${formatNumber(ms / 1000)}s`;
  };

  const getDifferenceIcon = (diff) => {
    if (Math.abs(diff) < 0.01) return <Equal className="w-4 h-4 text-gray-500" />;
    return diff > 0 ? 
      <TrendingUp className="w-4 h-4 text-red-500" /> : 
      <TrendingDown className="w-4 h-4 text-green-500" />;
  };

  const getDifferenceColor = (diff) => {
    if (Math.abs(diff) < 0.01) return "text-gray-500";
    return diff > 0 ? "text-red-500" : "text-green-500";
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Target className="w-5 h-5" />
            Algorithm Performance Comparison
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="p-1"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        <div className="p-6 space-y-6">
          {/* Test Location Input */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Test Parameters</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <label className="text-sm">Test Location:</label>
                  <input
                    type="number"
                    value={testLocation.x}
                    onChange={(e) => setTestLocation({...testLocation, x: parseInt(e.target.value)})}
                    className="w-20 px-2 py-1 text-sm border rounded"
                    placeholder="X"
                  />
                  <input
                    type="number"
                    value={testLocation.y}
                    onChange={(e) => setTestLocation({...testLocation, y: parseInt(e.target.value)})}
                    className="w-20 px-2 py-1 text-sm border rounded"
                    placeholder="Y"
                  />
                </div>
                <Button
                  onClick={handleCompare}
                  disabled={isLoading}
                  size="sm"
                >
                  <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                  Compare Algorithms
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Current System Performance */}
          {algorithmComparison && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Current System Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="text-xs text-gray-500">Algorithm</div>
                    <Badge variant="default">
                      {algorithmComparison.current_algorithm}
                    </Badge>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-gray-500">Total Cost</div>
                    <div className="font-mono text-sm">
                      {formatMs(algorithmComparison.current_performance?.total_cost || 0)}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-gray-500">Users</div>
                    <div className="font-mono text-sm flex items-center justify-center gap-1">
                      <Users className="w-3 h-3" />
                      {algorithmComparison.current_performance?.num_users || 0}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-gray-500">Cloudlets</div>
                    <div className="font-mono text-sm">
                      {algorithmComparison.current_performance?.num_cloudlets || 0}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Algorithm Comparison Results */}
          {algorithmComparison?.new_user_comparison && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Assignment Decision Comparison</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Test Location */}
                  <div className="text-sm text-gray-600 mb-4">
                    Testing user placement at location ({algorithmComparison.new_user_comparison.user_location.x}, {algorithmComparison.new_user_comparison.user_location.y})
                  </div>

                  {/* Algorithm Results Side by Side */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Greedy Results */}
                    <Card className="border-green-200">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-green-700">
                          Greedy Algorithm
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-600">Assigned Node:</span>
                            <Badge variant="outline">
                              {algorithmComparison.new_user_comparison.greedy_assignment.assigned_node}
                            </Badge>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-600">Distance:</span>
                            <span className="font-mono text-xs">
                              {formatNumber(algorithmComparison.new_user_comparison.greedy_assignment.distance)}px
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-600">Turnaround Time:</span>
                            <span className="font-mono text-xs">
                              {formatMs(algorithmComparison.new_user_comparison.greedy_assignment.estimated_turnaround_time)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-600">Cold Start Penalty:</span>
                            <span className="font-mono text-xs">
                              {formatMs(algorithmComparison.new_user_comparison.greedy_assignment.estimated_cold_start_penalty)}
                            </span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* CVX Results */}
                    <Card className="border-blue-200">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-blue-700">
                          CVX Optimization
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-600">Assigned Node:</span>
                            <Badge variant="outline">
                              {algorithmComparison.new_user_comparison.cvx_assignment.assigned_node}
                            </Badge>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-600">Distance:</span>
                            <span className="font-mono text-xs">
                              {formatNumber(algorithmComparison.new_user_comparison.cvx_assignment.distance)}px
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-600">Objective Value:</span>
                            <span className="font-mono text-xs">
                              {formatMs(algorithmComparison.new_user_comparison.cvx_assignment.optimization_objective_value)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-600">Latency Cost:</span>
                            <span className="font-mono text-xs">
                              {formatMs(algorithmComparison.new_user_comparison.cvx_assignment.latency_cost)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-gray-600">Cold Start Cost:</span>
                            <span className="font-mono text-xs">
                              {formatMs(algorithmComparison.new_user_comparison.cvx_assignment.cold_start_cost)}
                            </span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  <Separator />

                  {/* Performance Difference Analysis */}
                  <div className="space-y-3">
                    <h4 className="text-sm font-medium">Performance Analysis</h4>
                    
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                      <div className="flex items-center gap-2">
                        <span className="text-sm">Algorithm Agreement:</span>
                        <Badge 
                          variant={algorithmComparison.new_user_comparison.algorithm_agreement ? "default" : "destructive"}
                        >
                          {algorithmComparison.new_user_comparison.algorithm_agreement ? "✓ Agree" : "✗ Disagree"}
                        </Badge>
                      </div>
                      {!algorithmComparison.new_user_comparison.algorithm_agreement && (
                        <div className="text-xs text-gray-600">
                          Algorithms chose different nodes for optimal placement
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm flex items-center gap-2">
                          <Clock className="w-4 h-4" />
                          Turnaround Time Difference:
                        </span>
                        <div className={`flex items-center gap-1 font-mono text-sm ${getDifferenceColor(algorithmComparison.new_user_comparison.performance_difference.turnaround_time_diff)}`}>
                          {getDifferenceIcon(algorithmComparison.new_user_comparison.performance_difference.turnaround_time_diff)}
                          {formatMs(Math.abs(algorithmComparison.new_user_comparison.performance_difference.turnaround_time_diff))}
                        </div>
                      </div>

                      <div className="flex items-center justify-between">
                        <span className="text-sm flex items-center gap-2">
                          <Zap className="w-4 h-4" />
                          Cold Start Difference:
                        </span>
                        <div className={`flex items-center gap-1 font-mono text-sm ${getDifferenceColor(algorithmComparison.new_user_comparison.performance_difference.cold_start_diff)}`}>
                          {getDifferenceIcon(algorithmComparison.new_user_comparison.performance_difference.cold_start_diff)}
                          {formatMs(Math.abs(algorithmComparison.new_user_comparison.performance_difference.cold_start_diff))}
                        </div>
                      </div>
                    </div>

                    <div className="text-xs text-gray-600 p-2 bg-blue-50 rounded">
                      <strong>Interpretation:</strong> Negative differences indicate CVX performs better (lower cost). 
                      Positive differences indicate Greedy performs better.
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {!algorithmComparison && (
            <Card>
              <CardContent className="text-center py-8">
                <Target className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-4">No comparison data available</p>
                <Button onClick={handleCompare} disabled={isLoading}>
                  <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                  Run Algorithm Comparison
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
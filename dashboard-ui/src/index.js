import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

// shadcn/ui components
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "./components/ui/alert";
import { ButtonGroup, ButtonGroupItem } from "./components/ui/button-group";

// Lucide React icons
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Database,
  Globe,
  Monitor,
  Network,
  Server,
  Wifi,
  WifiOff,
  Zap,
  TrendingUp,
  Clock,
  Hash,
  Terminal,
  Filter,
  SortDesc,
  RotateCcw,
  ChevronUp,
} from "lucide-react";

// Utility function to format timestamps for display
function formatTimestamp(timestamp) {
  if (!timestamp) return "Unknown";

  try {
    const date = new Date(timestamp);
    // Format as: "14:30:25 (2 sec ago)"
    const timeString = date.toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });

    const now = new Date();
    const diffSeconds = Math.floor((now - date) / 1000);

    let relativeTime = "";
    if (diffSeconds < 60) {
      relativeTime = `${diffSeconds}s ago`;
    } else if (diffSeconds < 3600) {
      relativeTime = `${Math.floor(diffSeconds / 60)}m ago`;
    } else {
      relativeTime = `${Math.floor(diffSeconds / 3600)}h ago`;
    }

    return `${timeString} (${relativeTime})`;
  } catch (error) {
    // Fallback for old format or invalid timestamps
    return timestamp.toString();
  }
}

function TechnicalMetricCard({
  title,
  subtitle,
  icon: Icon,
  children,
  className = "",
  alert = false,
}) {
  return (
    <Card
      className={`metric-card tech-fade-in ${className} ${
        alert ? "border-red-500/50" : ""
      }`}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Icon
              className={`h-5 w-5 ${alert ? "text-red-400" : "text-blue-400"}`}
            />
            <CardTitle className="text-sm font-medium text-foreground">
              {title}
            </CardTitle>
          </div>
          <Badge variant="outline" className="text-xs text-muted-foreground">
            {subtitle}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-0">{children}</CardContent>
    </Card>
  );
}

function DataPoint({ label, value, isNew = false, statusCode = null }) {
  // Color coding for HTTP status codes
  const getStatusColor = (code) => {
    if (!code) return "text-blue-400";
    const numCode = parseInt(code);
    if (numCode >= 200 && numCode < 300) return "text-green-400"; // Success
    if (numCode >= 300 && numCode < 400) return "text-yellow-400"; // Redirect
    if (numCode >= 400 && numCode < 500) return "text-orange-400"; // Client Error
    if (numCode >= 500) return "text-red-400"; // Server Error
    return "text-blue-400";
  };

  const getBorderColor = (code) => {
    if (!code) return "border-blue-400";
    const numCode = parseInt(code);
    if (numCode >= 200 && numCode < 300) return "border-green-400";
    if (numCode >= 300 && numCode < 400) return "border-yellow-400";
    if (numCode >= 400 && numCode < 500) return "border-orange-400";
    if (numCode >= 500) return "border-red-400";
    return "border-blue-400";
  };

  return (
    <div
      className={`flex items-center justify-between py-2 px-3 rounded-md transition-all duration-200 min-w-0 ${
        isNew
          ? `bg-blue-500/20 border-l-2 ${getBorderColor(statusCode)}`
          : "hover:bg-blue-500/5"
      }`}
    >
      <span className="metric-label flex-1 min-w-0 mr-2">{label}</span>
      <span
        className={`metric-value flex-shrink-0 ${getStatusColor(statusCode)}`}
      >
        {value}
      </span>
    </div>
  );
}

function ConnectionStatus({ status }) {
  const isConnected = status === "Connected";
  return (
    <div className="connection-indicator">
      {isConnected ? (
        <Wifi className="h-4 w-4 text-green-400" />
      ) : (
        <WifiOff className="h-4 w-4 text-red-400" />
      )}
      <span className={isConnected ? "text-green-400" : "text-red-400"}>
        WebSocket: {status}
      </span>
      {isConnected && <div className="pulse-dot" />}
    </div>
  );
}

function AlertFilter({
  alertLimit,
  onLimitChange,
  totalAlerts,
  onClearAlerts,
}) {
  const limits = [10, 25, 50, 100];

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <Filter className="h-4 w-4 text-blue-400" />
          <span className="text-sm text-muted-foreground">Show:</span>
        </div>
        <ButtonGroup>
          {limits.map((limit) => (
            <ButtonGroupItem
              key={limit}
              active={alertLimit === limit}
              onClick={() => onLimitChange(limit)}
            >
              {limit}
            </ButtonGroupItem>
          ))}
        </ButtonGroup>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <SortDesc className="h-4 w-4 text-blue-400" />
          <span className="text-xs text-muted-foreground">
            Showing {Math.min(alertLimit, totalAlerts)} of {totalAlerts}
          </span>
        </div>
        {totalAlerts > 0 && (
          <button
            onClick={onClearAlerts}
            className="flex items-center space-x-1 text-xs text-red-400 hover:text-red-300 transition-colors"
          >
            <RotateCcw className="h-3 w-3" />
            <span>Clear All</span>
          </button>
        )}
      </div>
    </div>
  );
}

function RedisBloomViewer() {
  const [redisData, setRedisData] = useState({
    endpointFrequency: {},
    statusCodes: {},
    serviceCalls: [],
    systemFingerprints: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    const fetchRedisData = async () => {
      try {
        setError(null);
        const response = await fetch(
          `http://${window.location.hostname}:8080/redis-data`
        );
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setRedisData(data);
        setLastUpdate(new Date().toLocaleTimeString());
      } catch (error) {
        console.error("Failed to fetch Redis data:", error);
        setError(error.message);
      } finally {
        setLoading(false);
      }
    };

    fetchRedisData();
    const interval = setInterval(fetchRedisData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="flex items-center space-x-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
          <span className="text-muted-foreground">
            Initializing data streams...
          </span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive" className="mb-6">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Data Stream Error</AlertTitle>
        <AlertDescription>
          {error} - Check network connectivity and backend services.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6">
      {/* Endpoint Frequency */}
      <TechnicalMetricCard
        title="Endpoint Frequency"
        subtitle="Count-Min Sketch"
        icon={Globe}
      >
        <div className="scroll-container scroll-fade-both border border-blue-500/10 rounded-md bg-slate-950/30">
          <div className="scroll-content max-h-64 tech-scrollbar-dense space-y-1 p-2">
            {Object.entries(redisData.endpointFrequency).length > 0
              ? Object.entries(redisData.endpointFrequency).map(
                  ([endpoint, count]) => (
                    <DataPoint key={endpoint} label={endpoint} value={count} />
                  )
                )
              : // Test data to demonstrate scrolling when no real data
                [
                  "/api/users",
                  "/api/orders",
                  "/api/products",
                  "/api/auth",
                  "/api/data",
                  "/api/reports",
                  "/api/analytics",
                  "/api/settings",
                  "/api/admin",
                  "/api/health",
                  "/api/status",
                  "/api/logs",
                  "/api/dashboard",
                  "/api/notifications",
                  "/api/billing",
                  "/api/inventory",
                  "/api/customers",
                  "/api/suppliers",
                  "/api/categories",
                  "/api/search",
                ].map((endpoint) => (
                  <DataPoint
                    key={endpoint}
                    label={endpoint}
                    value={Math.floor(Math.random() * 1000)}
                  />
                ))}
          </div>
        </div>
      </TechnicalMetricCard>

      {/* Status Codes */}
      <TechnicalMetricCard
        title="HTTP Status Codes"
        subtitle="Count-Min Sketch"
        icon={Server}
      >
        <div className="scroll-container scroll-fade-both border border-blue-500/10 rounded-md bg-slate-950/30">
          <div className="scroll-content max-h-64 tech-scrollbar-dense space-y-1 p-2">
            {Object.entries(redisData.statusCodes).length > 0
              ? Object.entries(redisData.statusCodes).map(([code, count]) => (
                  <DataPoint
                    key={code}
                    label={`HTTP ${code}`}
                    value={count}
                    statusCode={code}
                    isNew={["500", "502", "503"].includes(code)}
                  />
                ))
              : // Test data to demonstrate scrolling when no real data
                [
                  200, 201, 202, 204, 206, 301, 302, 304, 400, 401, 403, 404,
                  405, 409, 422, 429, 500, 502, 503, 504,
                ].map((code) => (
                  <DataPoint
                    key={code}
                    label={`HTTP ${code}`}
                    value={Math.floor(Math.random() * 100)}
                    statusCode={code.toString()}
                    isNew={code >= 500}
                  />
                ))}
          </div>
        </div>
      </TechnicalMetricCard>

      {/* Service Calls */}
      <TechnicalMetricCard
        title="Service Calls"
        subtitle="Cuckoo Filter"
        icon={Network}
      >
        <div className="scroll-container scroll-fade-both border border-blue-500/10 rounded-md bg-slate-950/30">
          <div className="scroll-content max-h-64 tech-scrollbar space-y-2 p-2">
            {redisData.serviceCalls.length > 0
              ? redisData.serviceCalls.map((call, index) => (
                  <div key={index} className="data-point">
                    {call}
                  </div>
                ))
              : // Test data to demonstrate scrolling when no real data
                [
                  "service-a→service-b",
                  "service-b→data-collector",
                  "data-collector→redis",
                  "aggregator→redis",
                  "ai-service→redis",
                  "dashboard-bff→redis",
                  "service-a→dashboard-bff",
                  "redis-gears→redis",
                  "data-collector→ai-service",
                  "service-b→aggregator",
                  "dashboard-ui→dashboard-bff",
                  "service-a→data-collector",
                  "ai-service→dashboard-bff",
                  "aggregator→dashboard-bff",
                  "redis→redis-gears",
                  "dashboard-bff→service-a",
                  "service-b→redis-gears",
                  "data-collector→dashboard-bff",
                ].map((call, index) => (
                  <div key={index} className="data-point">
                    {call}
                  </div>
                ))}
          </div>
        </div>
      </TechnicalMetricCard>

      {/* System Fingerprints */}
      <TechnicalMetricCard
        title="System Fingerprints"
        subtitle="Stream Data"
        icon={Monitor}
      >
        <div className="scroll-container scroll-fade-both border border-blue-500/10 rounded-md bg-slate-950/30">
          <div className="scroll-content max-h-64 tech-scrollbar space-y-2 p-2">
            {redisData.systemFingerprints.length > 0
              ? redisData.systemFingerprints.map((fp, index) => (
                  <div
                    key={index}
                    className="p-2 rounded-md bg-slate-800/50 border border-blue-500/20"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-blue-400 font-mono">
                        {formatTimestamp(fp.timestamp)}
                      </span>
                      <Hash className="h-3 w-3 text-muted-foreground" />
                    </div>
                    <div className="data-stream-fingerprint text-green-400">
                      {fp.data}
                    </div>
                  </div>
                ))
              : // Test data to demonstrate scrolling when no real data
                Array.from({ length: 15 }, (_, index) => ({
                  timestamp: new Date(
                    Date.now() - index * 60000
                  ).toLocaleTimeString(),
                  data: `${Math.random()
                    .toString(36)
                    .substring(2, 15)}${Math.random()
                    .toString(36)
                    .substring(2, 15)}`,
                })).map((fp, index) => (
                  <div
                    key={index}
                    className="p-2 rounded-md bg-slate-800/50 border border-blue-500/20"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-blue-400 font-mono">
                        {formatTimestamp(fp.timestamp)}
                      </span>
                      <Hash className="h-3 w-3 text-muted-foreground" />
                    </div>
                    <div className="data-stream-fingerprint text-green-400">
                      {fp.data}
                    </div>
                  </div>
                ))}
          </div>
        </div>
      </TechnicalMetricCard>
    </div>
  );
}

function ScrollToTop() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const toggleVisibility = () => {
      if (window.pageYOffset > 300) {
        setIsVisible(true);
      } else {
        setIsVisible(false);
      }
    };

    window.addEventListener("scroll", toggleVisibility);
    return () => window.removeEventListener("scroll", toggleVisibility);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  if (!isVisible) return null;

  return (
    <button
      onClick={scrollToTop}
      className="fixed bottom-8 right-8 z-50 p-3 rounded-full bg-gradient-to-r from-blue-500/80 to-purple-500/80 hover:from-blue-400/90 hover:to-purple-400/90 text-white shadow-lg hover:shadow-xl transition-all duration-300 backdrop-blur-sm border border-blue-400/30 group"
      aria-label="Scroll to top"
    >
      <ChevronUp className="h-5 w-5 group-hover:scale-110 transition-transform duration-200" />
    </button>
  );
}

function App() {
  const [status, setStatus] = useState("NORMAL");
  const [logs, setLogs] = useState([]);
  const [alertLimit, setAlertLimit] = useState(25);
  const [connectionStatus, setConnectionStatus] = useState("Connecting...");
  const [systemStats, setSystemStats] = useState({
    uptime: "00:00:00",
    totalAlerts: 0,
    activeConnections: 1,
  });

  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.hostname}:8080`);

    ws.onopen = () => {
      setConnectionStatus("Connected");
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      setStatus("ANOMALOUS");
      setLogs((prev) => [
        { ...msg, timestamp: new Date().toLocaleTimeString(), id: Date.now() },
        ...prev,
      ]);
      setSystemStats((prev) => ({
        ...prev,
        totalAlerts: prev.totalAlerts + 1,
      }));
    };

    ws.onclose = () => {
      setConnectionStatus("Disconnected");
    };

    ws.onerror = () => {
      setConnectionStatus("Connection Error");
    };

    return () => ws.close();
  }, []);

  // Update uptime
  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const hours = Math.floor(elapsed / 3600000);
      const minutes = Math.floor((elapsed % 3600000) / 60000);
      const seconds = Math.floor((elapsed % 60000) / 1000);
      setSystemStats((prev) => ({
        ...prev,
        uptime: `${hours.toString().padStart(2, "0")}:${minutes
          .toString()
          .padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`,
      }));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Alert management functions
  const handleAlertLimitChange = (limit) => {
    setAlertLimit(limit);
  };

  const handleClearAlerts = () => {
    setLogs([]);
    setSystemStats((prev) => ({
      ...prev,
      totalAlerts: 0,
    }));
    setStatus("NORMAL");
  };

  // Get filtered alerts based on current limit
  const displayedAlerts = logs.slice(0, alertLimit);

  return (
    <div className="min-h-screen tech-bg-primary tech-grid-bg">
      <div className="container mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="tech-bg-card rounded-lg p-6 border border-blue-500/20">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Terminal className="h-8 w-8 text-blue-400" />
                <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  AI Anomaly Detection Dashboard
                </h1>
              </div>
            </div>
            <ConnectionStatus status={connectionStatus} />
          </div>

          <div className="flex items-center justify-between">
            <p className="text-muted-foreground">
              Real-time monitoring and analysis of system health
            </p>
            <div className="flex items-center space-x-6 text-sm">
              <div className="flex items-center space-x-2">
                <Clock className="h-4 w-4 text-blue-400" />
                <span className="font-mono">{systemStats.uptime}</span>
              </div>
              <div className="flex items-center space-x-2">
                <TrendingUp className="h-4 w-4 text-green-400" />
                <span>Active: {systemStats.activeConnections}</span>
              </div>
            </div>
          </div>

          <div className="mt-4 flex items-center space-x-4">
            <Badge
              variant={status === "NORMAL" ? "success" : "destructive"}
              className={`status-indicator ${
                status === "NORMAL" ? "status-normal" : "status-anomaly"
              }`}
            >
              {status === "NORMAL" ? (
                <CheckCircle className="h-3 w-3 mr-1" />
              ) : (
                <AlertTriangle className="h-3 w-3 mr-1" />
              )}
              System Status: {status}
            </Badge>
            <Badge variant="outline">
              <Zap className="h-3 w-3 mr-1" />
              {systemStats.totalAlerts} Total Alerts
            </Badge>
          </div>
        </div>

        {/* Alerts Section */}
        <Card className="tech-bg-card border-blue-500/20">
          <CardHeader>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <Activity className="h-5 w-5 text-orange-400" />
                <CardTitle>Recent Alerts</CardTitle>
              </div>
              <Badge variant="outline">{logs.length} alerts</Badge>
            </div>
            <AlertFilter
              alertLimit={alertLimit}
              onLimitChange={handleAlertLimitChange}
              totalAlerts={logs.length}
              onClearAlerts={handleClearAlerts}
            />
          </CardHeader>
          <CardContent>
            {displayedAlerts.length > 0 ? (
              <div className="scroll-container scroll-fade-both">
                <div className="scroll-content max-h-64 tech-scrollbar space-y-2">
                  {displayedAlerts.map((log) => (
                    <Alert
                      key={log.id || log.timestamp}
                      variant="destructive"
                      className="alert-critical"
                    >
                      <AlertTriangle className="h-4 w-4" />
                      <AlertTitle className="text-sm">
                        {formatTimestamp(log.timestamp)}
                      </AlertTitle>
                      <AlertDescription className="text-xs">
                        {log.message || log}
                      </AlertDescription>
                    </Alert>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-400 opacity-50" />
                <p>No alerts - System running normally</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Redis Data Viewer */}
        <RedisBloomViewer />
      </div>

      {/* Scroll to Top Button */}
      <ScrollToTop />
    </div>
  );
}

const root = createRoot(document.getElementById("root"));
root.render(<App />);

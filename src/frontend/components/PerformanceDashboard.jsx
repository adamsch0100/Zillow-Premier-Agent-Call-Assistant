import React, { useState, useEffect } from 'react';
import {
    LineChart,
    Line,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    Radar
} from 'recharts';
import '../styles/PerformanceDashboard.css';

const PerformanceDashboard = ({ agentId }) => {
    const [timeRange, setTimeRange] = useState('week');
    const [performanceData, setPerformanceData] = useState(null);
    const [teamData, setTeamData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedMetric, setSelectedMetric] = useState('conversion_rate');

    useEffect(() => {
        fetchPerformanceData();
    }, [timeRange, agentId]);

    const fetchPerformanceData = async () => {
        try {
            setLoading(true);
            
            // Fetch individual performance data
            const perfResponse = await fetch(
                `/api/analytics/performance/${agentId}?timeRange=${timeRange}`
            );
            if (!perfResponse.ok) throw new Error('Failed to fetch performance data');
            const perfData = await perfResponse.json();
            setPerformanceData(perfData);

            // Fetch team performance data
            const teamResponse = await fetch(
                `/api/analytics/performance/team?timeRange=${timeRange}`
            );
            if (!teamResponse.ok) throw new Error('Failed to fetch team data');
            const teamData = await teamResponse.json();
            setTeamData(teamData);

        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const formatPercentage = (value) => `${(value * 100).toFixed(1)}%`;
    const formatDuration = (seconds) => {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    };

    if (loading) return <div className="loading">Loading performance data...</div>;
    if (error) return <div className="error">{error}</div>;
    if (!performanceData || !teamData) return null;

    const radarData = [
        {
            metric: 'Conversion',
            value: performanceData.metrics.conversion_rate,
            average: teamData.avg_conversion_rate
        },
        {
            metric: 'Engagement',
            value: performanceData.metrics.client_engagement,
            average: teamData.avg_engagement
        },
        {
            metric: 'ALM',
            value: performanceData.metrics.alm_effectiveness,
            average: teamData.avg_alm_effectiveness
        },
        {
            metric: 'Follow-ups',
            value: performanceData.metrics.follow_up_rate,
            average: teamData.avg_follow_up_rate
        }
    ];

    return (
        <div className="performance-dashboard">
            <div className="dashboard-header">
                <h2>Agent Performance Dashboard</h2>
                <div className="time-range-selector">
                    <select 
                        value={timeRange} 
                        onChange={(e) => setTimeRange(e.target.value)}
                    >
                        <option value="day">Last 24 Hours</option>
                        <option value="week">Last Week</option>
                        <option value="month">Last Month</option>
                    </select>
                </div>
            </div>

            <div className="performance-summary">
                <div className="metric-card">
                    <h3>Total Calls</h3>
                    <p className="metric-value">{performanceData.summary.total_calls}</p>
                </div>
                <div className="metric-card">
                    <h3>Appointments Set</h3>
                    <p className="metric-value">{performanceData.summary.appointments_set}</p>
                </div>
                <div className="metric-card">
                    <h3>Conversion Rate</h3>
                    <p className="metric-value">
                        {formatPercentage(performanceData.metrics.conversion_rate)}
                    </p>
                </div>
                <div className="metric-card">
                    <h3>Avg Call Duration</h3>
                    <p className="metric-value">
                        {formatDuration(performanceData.metrics.avg_call_duration)}
                    </p>
                </div>
            </div>

            <div className="performance-grid">
                <div className="chart-container">
                    <h3>Performance Comparison</h3>
                    <ResponsiveContainer width="100%" height={400}>
                        <RadarChart data={radarData}>
                            <PolarGrid />
                            <PolarAngleAxis dataKey="metric" />
                            <PolarRadiusAxis tickFormatter={formatPercentage} />
                            <Radar
                                name="Agent"
                                dataKey="value"
                                stroke="#8884d8"
                                fill="#8884d8"
                                fillOpacity={0.6}
                            />
                            <Radar
                                name="Team Average"
                                dataKey="average"
                                stroke="#82ca9d"
                                fill="#82ca9d"
                                fillOpacity={0.6}
                            />
                            <Legend />
                        </RadarChart>
                    </ResponsiveContainer>
                </div>

                <div className="chart-container">
                    <h3>Trend Analysis</h3>
                    <div className="metric-selector">
                        <select
                            value={selectedMetric}
                            onChange={(e) => setSelectedMetric(e.target.value)}
                        >
                            <option value="conversion_rate">Conversion Rate</option>
                            <option value="client_engagement">Client Engagement</option>
                            <option value="alm_effectiveness">ALM Effectiveness</option>
                        </select>
                    </div>
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={performanceData.trends[selectedMetric]}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="date" />
                            <YAxis tickFormatter={formatPercentage} />
                            <Tooltip formatter={formatPercentage} />
                            <Legend />
                            <Line
                                type="monotone"
                                dataKey="value"
                                stroke="#8884d8"
                                activeDot={{ r: 8 }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="performance-analysis">
                <div className="analysis-section">
                    <h3>Strengths</h3>
                    <ul className="strength-list">
                        {performanceData.analysis.strengths.map((strength, index) => (
                            <li key={index} className="strength-item">
                                <span className="strength-icon">💪</span>
                                {strength}
                            </li>
                        ))}
                    </ul>
                </div>

                <div className="analysis-section">
                    <h3>Areas for Improvement</h3>
                    <ul className="improvement-list">
                        {performanceData.analysis.improvement_areas.map((area, index) => (
                            <li key={index} className="improvement-item">
                                <span className="improvement-icon">📈</span>
                                {area}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>

            <div className="team-comparison">
                <h3>Team Performance</h3>
                <div className="team-stats">
                    <div className="team-metric">
                        <label>Your Conversion Rate</label>
                        <div className="comparison-bar">
                            <div
                                className="your-performance"
                                style={{
                                    width: `${performanceData.metrics.conversion_rate * 100}%`
                                }}
                            />
                            <div
                                className="team-average"
                                style={{
                                    width: `${teamData.avg_conversion_rate * 100}%`
                                }}
                            />
                        </div>
                        <div className="comparison-legend">
                            <span className="your-label">You: {formatPercentage(performanceData.metrics.conversion_rate)}</span>
                            <span className="team-label">Team: {formatPercentage(teamData.avg_conversion_rate)}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default PerformanceDashboard;
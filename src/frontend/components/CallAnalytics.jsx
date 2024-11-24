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
    PieChart,
    Pie,
    Cell
} from 'recharts';
import '../styles/CallAnalytics.css';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

const CallAnalytics = () => {
    const [timeRange, setTimeRange] = useState('week');
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchMetrics();
    }, [timeRange]);

    const fetchMetrics = async () => {
        try {
            setLoading(true);
            const response = await fetch(`/api/analytics/metrics?timeRange=${timeRange}`);
            if (!response.ok) {
                throw new Error('Failed to fetch analytics data');
            }
            const data = await response.json();
            setMetrics(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const formatPercentage = (value) => `${(value * 100).toFixed(1)}%`;

    if (loading) return <div className="loading">Loading analytics...</div>;
    if (error) return <div className="error">{error}</div>;
    if (!metrics) return null;

    const almData = [
        { name: 'Appointment', value: metrics.average_alm_completion.appointment },
        { name: 'Location', value: metrics.average_alm_completion.location },
        { name: 'Motivation', value: metrics.average_alm_completion.motivation }
    ];

    const talkRatioData = [
        { name: 'Agent', value: metrics.average_talk_ratios.agent },
        { name: 'Client', value: metrics.average_talk_ratios.client },
        { name: 'Silence', value: metrics.average_talk_ratios.silence }
    ];

    return (
        <div className="call-analytics">
            <div className="analytics-header">
                <h2>Call Analytics Dashboard</h2>
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

            <div className="metrics-overview">
                <div className="metric-card">
                    <h3>Total Calls</h3>
                    <p className="metric-value">{metrics.total_calls}</p>
                </div>
                <div className="metric-card">
                    <h3>Appointment Rate</h3>
                    <p className="metric-value">{formatPercentage(metrics.appointment_success_rate)}</p>
                </div>
                <div className="metric-card">
                    <h3>Follow-up Rate</h3>
                    <p className="metric-value">{formatPercentage(metrics.follow_up_rate)}</p>
                </div>
                <div className="metric-card">
                    <h3>Avg. Engagement</h3>
                    <p className="metric-value">{formatPercentage(metrics.average_engagement)}</p>
                </div>
            </div>

            <div className="analytics-grid">
                <div className="chart-container">
                    <h3>ALM Framework Completion</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={almData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="name" />
                            <YAxis tickFormatter={formatPercentage} />
                            <Tooltip formatter={formatPercentage} />
                            <Legend />
                            <Bar dataKey="value" fill="#8884d8" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div className="chart-container">
                    <h3>Talk Time Distribution</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                            <Pie
                                data={talkRatioData}
                                dataKey="value"
                                nameKey="name"
                                cx="50%"
                                cy="50%"
                                outerRadius={100}
                                label={({ name, value }) => `${name}: ${formatPercentage(value)}`}
                            >
                                {talkRatioData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip formatter={formatPercentage} />
                            <Legend />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="call-success-factors">
                <h3>Call Success Factors</h3>
                <div className="success-metrics">
                    <div className="success-metric">
                        <label>Objection Handling Success</label>
                        <div className="progress-bar">
                            <div 
                                className="progress" 
                                style={{ width: `${metrics.outcomes?.objection_handling_success * 100}%` }}
                            />
                        </div>
                        <span>{formatPercentage(metrics.outcomes?.objection_handling_success || 0)}</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CallAnalytics;
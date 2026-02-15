import { useEffect, useState } from 'react';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell
} from 'recharts';
import { api } from '../api';
import Layout from '../components/Layout';

const COLORS = ['#6366f1', '#10b981', '#ef4444', '#f59e0b', '#8b5cf6', '#ec4899'];

const StatCard = ({ title, value }) => (
    <div className="card">
        <h3 className="text-sm text-secondary font-medium mb-2">{title}</h3>
        <p className="text-2xl font-bold">{value}</p>
    </div>
);

const Dashboard = () => {
    const [categoryStats, setCategoryStats] = useState([]);
    const [monthlyStats, setMonthlyStats] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [catData, monthData] = await Promise.all([
                    api.get('/stats/category'),
                    api.get('/stats/monthly')
                ]);
                setCategoryStats(catData);
                setMonthlyStats(monthData);
            } catch (err) {
                console.error("Failed to fetch stats:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const totalSpend = categoryStats.reduce((acc, curr) => acc + curr.total, 0);

    if (loading) return <Layout><div>Loading stats...</div></Layout>;

    return (
        <Layout>
            <div className="mb-8">
                <h2 className="text-2xl font-bold mb-2">Dashboard</h2>
                <p className="text-muted">Overview of your expenses</p>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <StatCard title="Total Spend" value={`₹${totalSpend.toFixed(2)}`} />
                <StatCard title="Top Category" value={categoryStats[0]?.category || 'N/A'} />
                <StatCard title="Recent Month" value={monthlyStats[monthlyStats.length - 1]?.total.toFixed(2) || '0'} />
            </div>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Category Chart */}
                <div className="card h-[400px] flex flex-col">
                    <h3 className="text-lg font-bold mb-4">Spend by Category</h3>
                    <div className="flex-1 min-h-0">
                        <ResponsiveContainer width="100%" height="80%">
                            <PieChart>
                                <Pie
                                    data={categoryStats}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    fill="#8884d8"
                                    paddingAngle={5}
                                    dataKey="total"
                                    nameKey="category"
                                >
                                    {categoryStats.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    formatter={(value) => `₹${value.toFixed(2)}`}
                                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                        {/* Legend */}
                        <div className="flex flex-wrap justify-center gap-4 mt-2 text-sm">
                            {categoryStats.slice(0, 5).map((entry, index) => (
                                <div key={index} className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }}></div>
                                    <span>{entry.category}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Monthly Chart */}
                <div className="card h-[400px] flex flex-col">
                    <h3 className="text-lg font-bold mb-4">Monthly Trends</h3>
                    <div className="flex-1 min-h-0">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={monthlyStats} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                                <XAxis dataKey="month" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                                <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `₹${value / 1000}k`} />
                                <Tooltip
                                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                                    formatter={(value) => [`₹${value.toFixed(2)}`, 'Spend']}
                                />
                                <Bar dataKey="total" fill="#6366f1" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default Dashboard;

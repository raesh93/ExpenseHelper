import { useEffect, useState, useMemo } from 'react';
import { Search, ChevronLeft, ChevronRight, Edit2, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { api } from '../api';
import Layout from '../components/Layout';

const Transactions = () => {
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const [hasMore, setHasMore] = useState(true);

    // Sorting State
    const [sortConfig, setSortConfig] = useState({ key: 'date', direction: 'desc' });

    // Quick Edit State
    const [editingId, setEditingId] = useState(null);
    const [editValue, setEditValue] = useState('');

    const LIMIT = 50; // Increased limit to make sorting more useful on client side

    const fetchTransactions = async () => {
        setLoading(true);
        try {
            const data = await api.get(`/transactions/?offset=${page * LIMIT}&limit=${LIMIT}`);
            setTransactions(data);
            if (data.length < LIMIT) setHasMore(false);
            else setHasMore(true);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTransactions();
    }, [page]);

    // Sorting Logic
    const sortedTransactions = useMemo(() => {
        let sortableItems = [...transactions];
        if (sortConfig.key !== null) {
            sortableItems.sort((a, b) => {
                let aValue = a[sortConfig.key];
                let bValue = b[sortConfig.key];

                // Handle numeric sorting for amount
                if (sortConfig.key === 'amount') {
                    aValue = parseFloat(aValue);
                    bValue = parseFloat(bValue);
                }

                // Handle date sorting
                if (sortConfig.key === 'date') {
                    aValue = new Date(aValue);
                    bValue = new Date(bValue);
                }

                if (aValue < bValue) {
                    return sortConfig.direction === 'asc' ? -1 : 1;
                }
                if (aValue > bValue) {
                    return sortConfig.direction === 'asc' ? 1 : -1;
                }
                return 0;
            });
        }
        return sortableItems;
    }, [transactions, sortConfig]);

    const requestSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const getSortIcon = (name) => {
        if (sortConfig.key !== name) return <ArrowUpDown size={14} className="opacity-30" />;
        return sortConfig.direction === 'asc'
            ? <ArrowUp size={14} className="text-blue-600" />
            : <ArrowDown size={14} className="text-blue-600" />;
    };

    const handleEdit = (txn) => {
        setEditingId(txn.id);
        setEditValue(txn.category || '');
    };

    const handleSave = async (id) => {
        try {
            const updated = await api.patch(`/transactions/${id}`, { category: editValue });
            setTransactions(prev => prev.map(t => t.id === id ? updated : t));
            setEditingId(null);
        } catch (err) {
            alert("Failed to update");
        }
    };

    const handleKeyDown = (e, id) => {
        if (e.key === 'Enter') handleSave(id);
        if (e.key === 'Escape') setEditingId(null);
    };

    return (
        <Layout>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h2 className="text-2xl font-bold mb-2 text-slate-800">Transactions</h2>
                    <p className="text-slate-500">Manage and categorize your spending</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setPage(p => Math.max(0, p - 1))}
                        disabled={page === 0}
                        className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-transparent transition-colors text-slate-600"
                    >
                        <ChevronLeft size={20} />
                    </button>
                    <span className="flex items-center px-4 font-medium text-slate-600 bg-slate-50 rounded-lg border border-slate-100">
                        Page {page + 1}
                    </span>
                    <button
                        onClick={() => setPage(p => p + 1)}
                        disabled={!hasMore}
                        className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-transparent transition-colors text-slate-600"
                    >
                        <ChevronRight size={20} />
                    </button>
                </div>
            </div>

            <div className="card overflow-hidden p-0 border border-slate-200 shadow-md">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-200">
                                <th
                                    className="p-4 text-sm font-semibold text-slate-700 cursor-pointer hover:bg-slate-100 transition-colors select-none"
                                    onClick={() => requestSort('date')}
                                >
                                    <div className="flex items-center gap-2">
                                        Date {getSortIcon('date')}
                                    </div>
                                </th>
                                <th className="p-4 text-sm font-semibold text-slate-700 w-1/3">
                                    Description
                                </th>
                                <th
                                    className="p-4 text-sm font-semibold text-slate-700 cursor-pointer hover:bg-slate-100 transition-colors select-none"
                                    onClick={() => requestSort('category')}
                                >
                                    <div className="flex items-center gap-2">
                                        Category {getSortIcon('category')}
                                    </div>
                                </th>
                                <th
                                    className="p-4 text-sm font-semibold text-slate-700 text-right cursor-pointer hover:bg-slate-100 transition-colors select-none"
                                    onClick={() => requestSort('amount')}
                                >
                                    <div className="flex items-center justify-end gap-2">
                                        Amount {getSortIcon('amount')}
                                    </div>
                                </th>
                                <th className="p-4 text-sm font-semibold text-slate-700 text-center">Type</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {loading ? (
                                <tr><td colSpan="5" className="p-12 text-center text-slate-500">Loading transactions...</td></tr>
                            ) : sortedTransactions.length === 0 ? (
                                <tr><td colSpan="5" className="p-12 text-center text-slate-500">No transactions found</td></tr>
                            ) : (
                                sortedTransactions.map((txn) => (
                                    <tr key={txn.id} className="group hover:bg-blue-50/30 transition-colors">
                                        <td className="p-4 font-mono text-sm text-slate-600 whitespace-nowrap">
                                            {txn.date}
                                        </td>
                                        <td className="p-4">
                                            <p className="line-clamp-2 text-sm font-medium text-slate-800 leading-snug" title={txn.description}>
                                                {txn.description}
                                            </p>
                                        </td>
                                        <td className="p-4">
                                            {editingId === txn.id ? (
                                                <input
                                                    autoFocus
                                                    className="bg-white border border-blue-500 ring-2 ring-blue-500/20 rounded px-2 py-1 text-sm text-slate-800 w-full focus:outline-none shadow-sm"
                                                    value={editValue}
                                                    onChange={(e) => setEditValue(e.target.value)}
                                                    onBlur={() => handleSave(txn.id)}
                                                    onKeyDown={(e) => handleKeyDown(e, txn.id)}
                                                />
                                            ) : (
                                                <div
                                                    className="flex items-center gap-2 cursor-pointer group/cat"
                                                    onClick={() => handleEdit(txn)}
                                                >
                                                    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border transition-colors ${txn.category
                                                        ? 'bg-blue-50 text-blue-700 border-blue-200 group-hover/cat:bg-blue-100 group-hover/cat:border-blue-300'
                                                        : 'bg-slate-100 text-slate-500 border-slate-200 group-hover/cat:bg-slate-200'
                                                        }`}>
                                                        {txn.category || 'Uncategorized'}
                                                    </span>
                                                    <Edit2 size={12} className="opacity-0 group-hover/cat:opacity-100 text-slate-400 hover:text-blue-600 transition-all" />
                                                </div>
                                            )}
                                        </td>
                                        <td className={`p-4 text-right font-mono text-sm font-medium ${txn.type === 'Credit' ? 'text-emerald-600' : 'text-slate-700'
                                            }`}>
                                            {txn.type === 'Credit' ? '+' : ''}₹{txn.amount.toLocaleString()}
                                        </td>
                                        <td className="p-4 text-center">
                                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide border ${txn.type === 'Credit'
                                                    ? 'bg-emerald-50 text-emerald-600 border-emerald-200'
                                                    : 'bg-slate-50 text-slate-500 border-slate-200'
                                                }`}>
                                                {txn.type === 'Credit' ? 'CR' : 'DR'}
                                            </span>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </Layout>
    );
};

export default Transactions;

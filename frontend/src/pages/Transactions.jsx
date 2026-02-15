import { useEffect, useState } from 'react';
import { Search, ChevronLeft, ChevronRight, Edit2 } from 'lucide-react';
import { api } from '../api';
import Layout from '../components/Layout';

const Transactions = () => {
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const [hasMore, setHasMore] = useState(true);

    // Quick Edit State
    const [editingId, setEditingId] = useState(null);
    const [editValue, setEditValue] = useState('');

    const LIMIT = 20;

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
                    <h2 className="text-2xl font-bold mb-2">Transactions</h2>
                    <p className="text-muted">Manage and categorize your spending</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setPage(p => Math.max(0, p - 1))}
                        disabled={page === 0}
                        className="px-3 py-2 disabled:opacity-50"
                    >
                        <ChevronLeft size={20} />
                    </button>
                    <span className="flex items-center px-2 text-sm text-muted">Page {page + 1}</span>
                    <button
                        onClick={() => setPage(p => p + 1)}
                        disabled={!hasMore}
                        className="px-3 py-2 disabled:opacity-50"
                    >
                        <ChevronRight size={20} />
                    </button>
                </div>
            </div>

            <div className="card overflow-hidden p-0">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-800/50">
                                <th className="p-4 text-sm font-medium text-muted border-b border-slate-700">Date</th>
                                <th className="p-4 text-sm font-medium text-muted border-b border-slate-700 w-1/3">Description</th>
                                <th className="p-4 text-sm font-medium text-muted border-b border-slate-700">Category</th>
                                <th className="p-4 text-sm font-medium text-muted border-b border-slate-700 text-right">Amount</th>
                                <th className="p-4 text-sm font-medium text-muted border-b border-slate-700">Type</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr><td colSpan="5" className="p-8 text-center text-muted">Loading...</td></tr>
                            ) : transactions.length === 0 ? (
                                <tr><td colSpan="5" className="p-8 text-center text-muted">No transactions found</td></tr>
                            ) : (
                                transactions.map((txn) => (
                                    <tr key={txn.id} className="group hover:bg-slate-800/30 transition-colors">
                                        <td className="p-4 border-b border-slate-700/50 font-mono text-sm text-slate-300">
                                            {txn.date}
                                        </td>
                                        <td className="p-4 border-b border-slate-700/50">
                                            <p className="line-clamp-1 text-sm font-medium text-slate-200" title={txn.description}>
                                                {txn.description}
                                            </p>
                                        </td>
                                        <td className="p-4 border-b border-slate-700/50">
                                            {editingId === txn.id ? (
                                                <input
                                                    autoFocus
                                                    className="bg-slate-900 border border-indigo-500 rounded px-2 py-1 text-sm text-white w-full focus:outline-none"
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
                                                    <span className={`px-2 py-1 rounded text-xs font-medium ${txn.category
                                                            ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                                                            : 'bg-slate-700/50 text-slate-400 border border-slate-700'
                                                        }`}>
                                                        {txn.category || 'Uncategorized'}
                                                    </span>
                                                    <Edit2 size={12} className="opacity-0 group-hover/cat:opacity-100 text-muted transition-opacity" />
                                                </div>
                                            )}
                                        </td>
                                        <td className={`p-4 border-b border-slate-700/50 text-right font-mono text-sm ${txn.type === 'Credit' ? 'text-emerald-400' : 'text-slate-200'
                                            }`}>
                                            {txn.type === 'Credit' ? '+' : ''}₹{txn.amount.toLocaleString()}
                                        </td>
                                        <td className="p-4 border-b border-slate-700/50">
                                            <span className={`text-xs ${txn.type === 'Credit' ? 'text-emerald-400' : 'text-slate-500'
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

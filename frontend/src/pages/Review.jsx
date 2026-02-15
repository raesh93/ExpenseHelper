import { useParams, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { Edit2, Save, Download, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import { api } from '../api';

const Review = () => {
    const { filename } = useParams();
    const location = useLocation();
    // Pass extracted transactions via state if coming from upload, else fetch?
    // For now, let's fetch all transactions for this source file.
    // The source_file path in DB matches the upload path.

    // Actually, we need to filter transactions by this file.
    // Our list endpoint supports basic filtering? No.
    // Let's rely on what we have:
    // 1. PDF URL: /api/files/{filename}
    // 2. Transactions: We might need to filter client side or add a filter to API.

    // For MVP transparency: We'll show ALL transactions today or just show the PDF for now.
    // Ideally we want to see transactions belonging to this PDF.

    // Let's implement a client-side filter for now since we don't have source_file filter in API yet.

    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);
    const pdfUrl = `/api/files/${filename}`;

    useEffect(() => {
        const fetchTxns = async () => {
            // Fetch recent transactions (limit 100) and filter by filename
            // This is hacky but consistent with our MVP plan.
            try {
                const data = await api.get('/transactions/?limit=200');
                // Filter where source_file contains filename
                const filtered = data.filter(t => t.source_file && t.source_file.includes(filename));
                setTransactions(filtered);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        }
        fetchTxns();
    }, [filename]);

    return (
        <Layout>
            <div className="flex items-center gap-4 mb-4">
                <Link to="/files" className="p-2 rounded-full hover:bg-slate-200 text-slate-500 transition-colors">
                    <ArrowLeft size={20} />
                </Link>
                <div className="flex flex-col">
                    <h2 className="text-xl font-bold text-slate-900">Review Statement</h2>
                    <span className="text-xs text-slate-500 font-mono">
                        {filename}
                    </span>
                </div>
            </div>

            {/* Main Layout - PDF takes priority */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-140px)]">
                {/* Left Panel: PDF Viewer (Larger) */}
                <div className="lg:col-span-7 xl:col-span-8 card p-0 overflow-hidden h-full flex flex-col bg-slate-900/5 shadow-inner">
                    <div className="p-3 border-b border-slate-200 bg-white flex justify-between items-center text-xs text-slate-500">
                        <span className="font-semibold text-slate-700">PDF Preview</span>
                        <span>If password protected, enter it in the viewer</span>
                    </div>
                    <iframe
                        src={pdfUrl}
                        className="w-full h-full border-none"
                        title="PDF Viewer"
                    />
                </div>

                {/* Right Panel: Extracted Transactions */}
                <div className="lg:col-span-5 xl:col-span-4 card p-0 overflow-hidden h-full flex flex-col">
                    <div className="p-4 border-b border-slate-100 bg-slate-50">
                        <h3 className="font-bold text-sm text-slate-700">Extracted Transactions ({transactions.length})</h3>
                    </div>

                    <div className="overflow-y-auto flex-1 p-0 bg-white">
                        <table className="w-full text-left text-sm border-collapse">
                            <thead className="sticky top-0 bg-slate-50 z-10 shadow-sm">
                                <tr>
                                    <th className="p-3 font-semibold text-slate-600 border-b border-slate-200">Date</th>
                                    <th className="p-3 font-semibold text-slate-600 border-b border-slate-200">Description</th>
                                    <th className="p-3 font-semibold text-slate-600 border-b border-slate-200 text-right">Amount</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading ? (
                                    <tr><td colSpan="3" className="p-4 text-center text-slate-500">Loading...</td></tr>
                                ) : transactions.length === 0 ? (
                                    <tr><td colSpan="3" className="p-4 text-center text-slate-500">No transactions found for this file</td></tr>
                                ) : (
                                    transactions.map((t, idx) => (
                                        <tr key={t.id || idx} className="border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer">
                                            <td className="p-3 font-mono text-slate-500 whitespace-nowrap text-xs">{t.date}</td>
                                            <td className="p-3 text-slate-700 line-clamp-1 text-xs">{t.description}</td>
                                            <td className={`p-3 text-right font-mono text-xs font-medium ${t.type === 'Credit' ? 'text-emerald-600' : 'text-slate-700'}`}>
                                                {t.amount.toLocaleString()}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default Review;

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import { Eye, FileText, Trash2, Search } from 'lucide-react';
import { api } from '../api';

const FilesPage = () => {
    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

    useEffect(() => {
        const fetchFiles = async () => {
            try {
                // Since we don't have a dedicated "list files" endpoint that returns metadata from DB
                // We will fetch unique source_files from transactions for now, 
                // OR better, let's implement a proper endpoint in backend quickly?
                // For now, let's use the transaction aggregation as a proxy or just list raw files if possible.
                // Actually, the best way in Phase 5 is to have a real endpoint.
                // Let's assume we'll add one. For now, let's mock/aggregate from transactions.

                const txns = await api.get('/transactions/?limit=1000');
                const fileMap = {};

                txns.forEach(t => {
                    if (!t.source_file) return;
                    const filename = t.source_file.split('/').pop();
                    if (!fileMap[filename]) {
                        fileMap[filename] = {
                            name: filename,
                            count: 0,
                            totalAmount: 0,
                            lastDate: t.date,
                            id: filename // using filename as ID for now
                        };
                    }
                    fileMap[filename].count++;
                    fileMap[filename].totalAmount += t.amount;
                    if (t.date > fileMap[filename].lastDate) fileMap[filename].lastDate = t.date;
                });

                setFiles(Object.values(fileMap));
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchFiles();
    }, []);

    const filteredFiles = files.filter(f => f.name.toLowerCase().includes(search.toLowerCase()));

    return (
        <Layout>
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold text-slate-800">Preprocessed Files</h1>
                <div className="relative w-64">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input
                        type="text"
                        placeholder="Search files..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="input-field pl-10"
                    />
                </div>
            </div>

            <div className="card p-0 overflow-hidden">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-slate-50 border-b border-slate-200">
                        <tr>
                            <th className="p-4 font-semibold text-slate-600">Filename</th>
                            <th className="p-4 font-semibold text-slate-600 text-center">Transactions</th>
                            <th className="p-4 font-semibold text-slate-600 text-right">Total Amount</th>
                            <th className="p-4 font-semibold text-slate-600 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            <tr><td colSpan="4" className="p-8 text-center text-slate-500">Loading files...</td></tr>
                        ) : filteredFiles.length === 0 ? (
                            <tr><td colSpan="4" className="p-8 text-center text-slate-500">No files found</td></tr>
                        ) : (
                            filteredFiles.map((file) => (
                                <tr key={file.id} className="border-b border-slate-100 hover:bg-slate-50">
                                    <td className="p-4">
                                        <div className="flex items-center gap-3">
                                            <div className="p-2 bg-blue-100 text-blue-600 rounded-lg">
                                                <FileText size={20} />
                                            </div>
                                            <span className="font-medium text-slate-700">{file.name}</span>
                                        </div>
                                    </td>
                                    <td className="p-4 text-center">
                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800">
                                            {file.count}
                                        </span>
                                    </td>
                                    <td className="p-4 text-right font-mono text-slate-600">
                                        {file.totalAmount.toLocaleString()}
                                    </td>
                                    <td className="p-4 text-right">
                                        <Link
                                            to={`/review/${file.name}`}
                                            className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-800"
                                        >
                                            <Eye size={16} /> Review
                                        </Link>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </Layout>
    );
};

export default FilesPage;

import { useState } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../api';
import Layout from '../components/Layout';

const UploadPage = () => {
    const [file, setFile] = useState(null);
    const [password, setPassword] = useState('');
    const [status, setStatus] = useState('idle'); // idle, uploading, success, error
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const handleFileChange = (e) => {
        if (e.target.files[0]) {
            setFile(e.target.files[0]);
            setStatus('idle');
            setResult(null);
            setError(null);
        }
    };

    const cleanFilename = (name) => {
        // Remove UUID prefix if present from previous uploads (not relevant here since we are picking local file)
        // But mainly just display name
        return name;
    }

    const handleUpload = async (e) => {
        e.preventDefault();
        if (!file) return;

        setStatus('uploading');
        setError(null);

        const formData = new FormData();
        formData.append('file', file);
        if (password) {
            formData.append('password', password);
        }

        try {
            const res = await api.post('/upload/', formData);
            setResult(res);
            setStatus('success');
            // Navigate to review after short delay or show button
            if (res.saved_filename) {
                window.location.href = `/review/${res.saved_filename}`;
            }
        } catch (err) {
            console.error(err);
            setError(err.message || "Upload failed");
            setStatus('error');
        }
    };

    return (
        <Layout>
            <div className="max-w-2xl mx-auto">
                <div className="mb-8 text-center">
                    <h2 className="text-3xl font-bold mb-2">Upload Statement</h2>
                    <p className="text-muted">Supports ICICI Credit Card & Kotak Debit Card PDFs</p>
                </div>

                <div className="card">
                    <form onSubmit={handleUpload} className="flex flex-col gap-6">
                        {/* Dropzone Area */}
                        <div className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors ${file ? 'border-indigo-500/50 bg-indigo-500/5' : 'border-slate-700 hover:border-slate-600'
                            }`}>
                            <input
                                type="file"
                                id="file-upload"
                                className="hidden"
                                accept=".pdf"
                                onChange={handleFileChange}
                            />

                            <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center gap-4">
                                <div className="p-4 rounded-full bg-slate-800 text-indigo-400">
                                    {file ? <FileText size={32} /> : <Upload size={32} />}
                                </div>
                                <div>
                                    {file ? (
                                        <p className="text-lg font-medium text-white">{file.name}</p>
                                    ) : (
                                        <>
                                            <p className="text-lg font-medium text-white">Click to upload or drag and drop</p>
                                            <p className="text-sm text-muted mt-1">PDF files only (max 10MB)</p>
                                        </>
                                    )}
                                </div>
                            </label>
                        </div>

                        {/* Password Field */}
                        <div>
                            <label className="block text-sm font-medium text-muted mb-2">
                                PDF Password (Optional)
                            </label>
                            <input
                                type="password"
                                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-indigo-500 transition-colors"
                                placeholder="Enter password if encrypted"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                            <p className="text-xs text-muted mt-2">
                                We process the password only to unlock the file temporarily.
                            </p>
                        </div>

                        {/* Action Button */}
                        <button
                            type="submit"
                            disabled={!file || status === 'uploading'}
                            className="btn-primary w-full py-3 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {status === 'uploading' ? (
                                <>
                                    <Loader2 className="animate-spin" size={20} />
                                    Processing...
                                </>
                            ) : (
                                <>
                                    <Upload size={20} />
                                    Upload & Extract
                                </>
                            )}
                        </button>
                    </form>
                </div>

                {/* Status Messages */}
                {status === 'success' && result && (
                    <div className="mt-6 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-start gap-3">
                        <CheckCircle className="shrink-0 mt-0.5" size={20} />
                        <div>
                            <h4 className="font-bold">Extraction Successful!</h4>
                            <p className="text-sm mt-1">
                                Processed using <b>{result.extractor}</b>.
                                Found <b>{result.transactions_found}</b> transactions
                                ({result.transactions_saved} saved).
                            </p>
                        </div>
                    </div>
                )}

                {status === 'error' && error && (
                    <div className="mt-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 flex items-start gap-3">
                        <AlertCircle className="shrink-0 mt-0.5" size={20} />
                        <div>
                            <h4 className="font-bold">Extraction Failed</h4>
                            <p className="text-sm mt-1">{error}</p>
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default UploadPage;

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
            const selectedFile = e.target.files[0];
            setFile(selectedFile);
            setStatus('idle');
            setResult(null);
            setError(null);

            // Auto-extract password from filename
            // Format: ..._password.pdf
            const parts = selectedFile.name.split('_');
            if (parts.length > 1) {
                const lastPart = parts[parts.length - 1];
                const potentialPassword = lastPart.replace('.pdf', '');
                if (potentialPassword) {
                    setPassword(potentialPassword);
                }
            }
        }
    };

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
                // Optional: Auto redirect
                // window.location.href = `/review/${res.saved_filename}`;
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
                    <h2 className="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                        Upload Statement
                    </h2>
                    <p className="text-slate-500">
                        Supports ICICI Credit Card & Kotak Debit Card PDFs
                    </p>
                </div>

                <div className="card bg-white/50 backdrop-blur-sm shadow-xl border-slate-200/60">
                    <form onSubmit={handleUpload} className="flex flex-col gap-6">
                        {/* Dropzone Area */}
                        <div className={`
                            relative overflow-hidden group
                            border-2 border-dashed rounded-xl p-10 text-center transition-all duration-300
                            ${file
                                ? 'border-emerald-500/50 bg-emerald-50/50'
                                : 'border-slate-300 hover:border-blue-500 hover:bg-blue-50/50'
                            }
                        `}>
                            <input
                                type="file"
                                id="file-upload"
                                className="hidden"
                                accept=".pdf"
                                onChange={handleFileChange}
                            />

                            <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center gap-4 relative z-10">
                                <div className={`
                                    p-4 rounded-full transition-all duration-300 shadow-sm
                                    ${file ? 'bg-emerald-100 text-emerald-600' : 'bg-white text-blue-600 group-hover:scale-110 group-hover:shadow-md'}
                                `}>
                                    {file ? <FileText size={32} /> : <Upload size={32} />}
                                </div>
                                <div>
                                    {file ? (
                                        <p className="text-lg font-medium text-slate-800">{file.name}</p>
                                    ) : (
                                        <>
                                            <p className="text-lg font-medium text-slate-700">
                                                Click to upload or drag and drop
                                            </p>
                                            <p className="text-sm text-slate-400 mt-1">
                                                PDF files only (max 10MB)
                                            </p>
                                        </>
                                    )}
                                </div>
                            </label>
                        </div>

                        {/* Password Field */}
                        <div className="space-y-2">
                            <label className="block text-sm font-medium text-slate-700">
                                PDF Password <span className="text-slate-400 font-normal">(Auto-detected)</span>
                            </label>
                            <div className="relative">
                                <input
                                    type="password"
                                    className="w-full bg-white border border-slate-200 rounded-lg px-4 py-3 
                                    text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 
                                    transition-all shadow-sm placeholder:text-slate-300"
                                    placeholder="Enter password if encrypted"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                                {password && (
                                    <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md">
                                        Detected
                                    </div>
                                )}
                            </div>
                            <p className="text-xs text-slate-500">
                                We process the password only to unlock the file temporarily.
                            </p>
                        </div>

                        {/* Action Button */}
                        <button
                            type="submit"
                            disabled={!file || status === 'uploading'}
                            className={`
                                w-full py-3.5 rounded-lg flex items-center justify-center gap-2 font-medium text-white
                                transition-all duration-300 shadow-lg shadow-blue-500/20
                                ${!file || status === 'uploading'
                                    ? 'bg-slate-300 cursor-not-allowed shadow-none'
                                    : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 hover:shadow-blue-500/40 active:scale-[0.98]'
                                }
                            `}
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
                    <div className="mt-6 p-4 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-800 flex items-start gap-4 shadow-sm animate-in fade-in slide-in-from-bottom-2">
                        <div className="p-2 bg-emerald-100 rounded-full shrink-0">
                            <CheckCircle size={20} className="text-emerald-600" />
                        </div>
                        <div className="flex-1">
                            <h4 className="font-bold text-lg">Extraction Successful!</h4>
                            <p className="text-sm mt-1 text-emerald-600/80">
                                Processed using <span className="font-mono font-medium">{result.extractor}</span>.
                                <br />
                                Found <span className="font-bold">{result.transactions_found}</span> transactions
                                ({result.transactions_saved} new saved).
                            </p>

                            {result.saved_filename && (
                                <a
                                    href={`/review/${result.saved_filename}`}
                                    className="inline-flex items-center gap-1 mt-3 text-sm font-semibold text-emerald-700 hover:text-emerald-900 border-b border-emerald-700/30 hover:border-emerald-900"
                                >
                                    Review Transactions &rarr;
                                </a>
                            )}
                        </div>
                    </div>
                )}

                {status === 'error' && error && (
                    <div className="mt-6 p-4 rounded-xl bg-red-50 border border-red-100 text-red-800 flex items-start gap-4 shadow-sm animate-in fade-in slide-in-from-bottom-2">
                        <div className="p-2 bg-red-100 rounded-full shrink-0">
                            <AlertCircle size={20} className="text-red-600" />
                        </div>
                        <div>
                            <h4 className="font-bold text-lg">Extraction Failed</h4>
                            <p className="text-sm mt-1 text-red-600/80">{error}</p>
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default UploadPage;

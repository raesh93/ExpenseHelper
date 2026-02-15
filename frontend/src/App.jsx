import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Transactions from './pages/Transactions';
import UploadPage from './pages/Upload';
import Review from './pages/Review';
import FilesPage from './pages/Files';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/files" element={<FilesPage />} />
        <Route path="/review/:filename" element={<Review />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

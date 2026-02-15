import { Link, useLocation } from 'react-router-dom';
import { Home, Upload, FileText, PieChart, Files, Menu } from 'lucide-react';
import { useState } from 'react';

const Layout = ({ children }) => {
  const location = useLocation();
  const [isSidebarOpen, setSidebarOpen] = useState(true);

  const navItems = [
    { path: '/', label: 'Dashboard', icon: Home },
    { path: '/transactions', label: 'Transactions', icon: FileText },
    { path: '/files', label: 'Files', icon: Files },
    { path: '/upload', label: 'Upload', icon: Upload },
  ];

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      {/* Sidebar */}
      <aside
        className={`${isSidebarOpen ? 'w-64' : 'w-20'} 
        bg-white border-r border-slate-200 transition-all duration-300 flex flex-col fixed h-full z-20`}
      >
        <div className="p-4 flex items-center justify-between border-b border-slate-100">
          <div className={`flex items-center gap-2 font-bold text-xl text-primary ${!isSidebarOpen && 'hidden'}`}>
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white">
              EH
            </div>
            ExpenseHelper
          </div>
          <button onClick={() => setSidebarOpen(!isSidebarOpen)} className="p-1 hover:bg-slate-100 rounded">
            <Menu size={20} className="text-slate-500" />
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors
                  ${isActive
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`}
              >
                <Icon size={20} />
                {isSidebarOpen && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-100">
          {isSidebarOpen && <div className="text-xs text-slate-400">v1.0.0</div>}
        </div>
      </aside>

      {/* Main Content */}
      <main className={`flex-1 transition-all duration-300 ${isSidebarOpen ? 'ml-64' : 'ml-20'}`}>
        <div className="container mx-auto p-8 max-w-7xl">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
